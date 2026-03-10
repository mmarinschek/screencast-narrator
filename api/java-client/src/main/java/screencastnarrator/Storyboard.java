package screencastnarrator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

import screencastnarrator.generated.HighlightStyle;
import screencastnarrator.generated.ScreenAction.ScreenActionTiming;

public class Storyboard {

    private static final Logger LOG = Logger.getLogger(Storyboard.class.getName());

    @FunctionalInterface
    public interface Action {
        void execute(Storyboard storyboard) throws Exception;
    }

    private final SharedConfig config;
    private final Path outputDir;
    private final Page page;
    private final String language;
    private final int videoWidth;
    private final int videoHeight;
    private final List<Map<String, Object>> narrations = new ArrayList<>();
    private int narrationIdCounter = 0;
    private int screenActionIdCounter = 0;
    private int highlightIdCounter = 0;
    private boolean narrationOpen = false;
    private String pendingText = null;
    private Map<String, String> pendingTranslations = new LinkedHashMap<>();
    private int pendingNarrationId = -1;
    private final List<Map<String, Object>> pendingScreenActions = new ArrayList<>();
    private final List<Map<String, Object>> pendingHighlights = new ArrayList<>();
    private Integer pendingActionId = null;
    private String pendingVoice = null;
    private HighlightStyle highlightStyle;
    private final boolean debugOverlay;
    private final int fontSize;
    private Map<String, Map<String, String>> voices;

    private CdpVideoRecorder currentRecorder;
    private long narrationStartTimeNanos;

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle,
                       boolean debugOverlay, int fontSize, Map<String, Map<String, String>> voices) throws Exception {
        this(outputDir, page, language, highlightStyle, debugOverlay, fontSize, voices, 1280, 720);
    }

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle,
                       boolean debugOverlay, int fontSize, Map<String, Map<String, String>> voices,
                       int videoWidth, int videoHeight) throws Exception {
        this.config = SharedConfig.load();
        this.outputDir = outputDir;
        this.page = page;
        this.language = language;
        this.videoWidth = videoWidth;
        this.videoHeight = videoHeight;
        this.highlightStyle = highlightStyle != null ? highlightStyle : new HighlightStyle();
        this.debugOverlay = debugOverlay;
        this.fontSize = fontSize;
        this.voices = voices;
        Files.createDirectories(outputDir);
    }

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle,
                       boolean debugOverlay, int fontSize) throws Exception {
        this(outputDir, page, language, highlightStyle, debugOverlay, fontSize, null);
    }

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle,
                       boolean debugOverlay) throws Exception {
        this(outputDir, page, language, highlightStyle, debugOverlay, 24, null);
    }

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle) throws Exception {
        this(outputDir, page, language, highlightStyle, false, 24, null);
    }

    public Storyboard(Path outputDir, Page page, String language) throws Exception {
        this(outputDir, page, language, null, false, 24, null);
    }

    public Storyboard(Path outputDir, Page page) throws Exception {
        this(outputDir, page, "en");
    }

    public Storyboard(Path outputDir) throws Exception {
        this(outputDir, null, "en");
    }

    public HighlightStyle getHighlightStyle() {
        return highlightStyle;
    }

    public Storyboard withHighlightStyle(HighlightStyle style) {
        this.highlightStyle = HighlightStyles.merge(this.highlightStyle, style);
        return this;
    }

    public int beginNarration() throws Exception {
        return beginNarration(null, Map.of(), null);
    }

    public int beginNarration(String text) throws Exception {
        return beginNarration(text, Map.of(), null);
    }

    public int beginNarration(String text, Map<String, String> translations) throws Exception {
        return beginNarration(text, translations, null);
    }

    public int beginNarration(String text, Map<String, String> translations, String voice) throws Exception {
        if (narrationOpen) {
            throw new IllegalStateException(
                "Cannot begin a new narration while another is still open");
        }
        int nid = narrationIdCounter++;
        narrationOpen = true;
        pendingNarrationId = nid;
        pendingText = text;
        pendingVoice = voice;
        pendingTranslations = new LinkedHashMap<>(translations);
        pendingScreenActions.clear();
        pendingHighlights.clear();

        if (page != null) {
            startRecording(nid);
        }

        return nid;
    }

    private void startRecording(int narrationId) throws IOException {
        Path videoDir = outputDir.resolve("videos");
        Path videoFile = videoDir.resolve(String.format("narration-%03d.mp4", narrationId));
        currentRecorder = new CdpVideoRecorder(page, videoFile, videoWidth, videoHeight, config);
        currentRecorder.start();
        narrationStartTimeNanos = System.nanoTime();
    }

    private void stopRecording() {
        if (currentRecorder == null) return;
        try {
            currentRecorder.stop();
            LOG.info(String.format("Narration %d video saved: %s (%d frames)",
                    pendingNarrationId, currentRecorder.getOutputFile(), currentRecorder.getFrameCount()));
        } catch (Exception e) {
            throw new RuntimeException("Failed to stop CDP video recording for narration " + pendingNarrationId, e);
        } finally {
            currentRecorder = null;
        }
    }

    private long elapsedMs() {
        return (System.nanoTime() - narrationStartTimeNanos) / 1_000_000;
    }

    public int beginScreenAction(String description) throws Exception {
        return beginScreenAction(description, ScreenActionTiming.CASTED, null);
    }

    public int beginScreenAction() throws Exception {
        return beginScreenAction(null, ScreenActionTiming.CASTED, null);
    }

    public int beginScreenAction(String description, ScreenActionTiming timing, Integer durationMs) throws Exception {
        if (!narrationOpen) {
            throw new IllegalStateException(
                "Cannot begin a screen action outside of a narration bracket");
        }
        if (pendingActionId != null) {
            throw new IllegalStateException(
                "Cannot begin a new screen action while another is still open");
        }
        if (timing == ScreenActionTiming.TIMED && durationMs == null) {
            throw new IllegalArgumentException(
                "durationMs is required when timing is 'timed'");
        }
        int said = screenActionIdCounter++;
        Map<String, Object> action = new LinkedHashMap<>();
        action.put("screenActionId", said);
        if (description != null) {
            action.put("description", description);
        }
        if (timing != ScreenActionTiming.CASTED) {
            action.put("timing", timing.value());
        }
        if (durationMs != null) {
            action.put("durationMs", durationMs);
        }
        action.put("startOffsetMs", elapsedMs());
        pendingScreenActions.add(action);
        pendingActionId = said;
        return said;
    }

    public void highlight(Locator locator) throws Exception {
        if (page == null) {
            throw new IllegalStateException("Cannot highlight: no page was provided to Storyboard");
        }
        if (!narrationOpen) {
            throw new IllegalStateException("Cannot highlight outside of a narration bracket");
        }
        int hid = highlightIdCounter++;
        SharedConfig hlConfig = config.withHighlightOverrides(highlightStyle);
        long startOffset = elapsedMs();
        Highlight.highlight(page, locator, hlConfig);
        long endOffset = elapsedMs();
        Map<String, Object> hl = new LinkedHashMap<>();
        hl.put("highlightId", hid);
        hl.put("startOffsetMs", startOffset);
        hl.put("endOffsetMs", endOffset);
        pendingHighlights.add(hl);
    }

    public void done() throws Exception {
        if (narrationOpen) {
            throw new IllegalStateException("Cannot finalize: a narration bracket is still open");
        }
        flush();
    }

    public void endScreenAction() throws Exception {
        if (pendingActionId == null) {
            throw new IllegalStateException(
                "Cannot end screen action: no screen action is open");
        }
        for (Map<String, Object> action : pendingScreenActions) {
            if (pendingActionId.equals(action.get("screenActionId"))) {
                action.put("endOffsetMs", elapsedMs());
                break;
            }
        }
        pendingActionId = null;
    }

    public void endNarration() throws Exception {
        if (!narrationOpen) {
            throw new IllegalStateException(
                "Cannot end narration: no narration bracket is open");
        }
        if (pendingActionId != null) {
            throw new IllegalStateException(
                "Cannot end narration while a screen action is still open");
        }

        stopRecording();

        Map<String, Object> narration = new LinkedHashMap<>();
        narration.put("narrationId", pendingNarrationId);
        if (pendingText != null) {
            narration.put("text", pendingText);
        }
        if (pendingVoice != null) {
            narration.put("voice", pendingVoice);
        }
        if (!pendingTranslations.isEmpty()) {
            narration.put("translations", new LinkedHashMap<>(pendingTranslations));
        }
        narration.put("videoFile", String.format("videos/narration-%03d.mp4", pendingNarrationId));
        if (!pendingScreenActions.isEmpty()) {
            narration.put("screenActions", new ArrayList<>(pendingScreenActions));
        }
        if (!pendingHighlights.isEmpty()) {
            narration.put("highlights", new ArrayList<>(pendingHighlights));
        }
        narrations.add(narration);
        narrationOpen = false;
        pendingText = null;
        pendingVoice = null;
        pendingTranslations = new LinkedHashMap<>();
        pendingNarrationId = -1;
        pendingScreenActions.clear();
        pendingHighlights.clear();
        flush();
    }

    public int narrate(String text, Action action) throws Exception {
        return narrate(text, Map.of(), null, action);
    }

    public int narrate(String text, Map<String, String> translations, Action action) throws Exception {
        return narrate(text, translations, null, action);
    }

    public int narrate(String text, Map<String, String> translations, String voice, Action action) throws Exception {
        int nid = beginNarration(text, translations, voice);
        try {
            action.execute(this);
        } finally {
            if (pendingActionId != null) {
                endScreenAction();
            }
            endNarration();
        }
        return nid;
    }

    public int screenAction(Action action) throws Exception {
        return screenAction(null, ScreenActionTiming.CASTED, null, action);
    }

    public int screenAction(String description, Action action) throws Exception {
        return screenAction(description, ScreenActionTiming.CASTED, null, action);
    }

    public int screenAction(String description, ScreenActionTiming timing, Integer durationMs, Action action) throws Exception {
        int said = beginScreenAction(description, timing, durationMs);
        try {
            action.execute(this);
        } finally {
            endScreenAction();
        }
        return said;
    }

    private void flush() throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("language", language);
        root.put("narrations", narrations);
        Map<String, Object> options = new LinkedHashMap<>();
        HighlightStyle hs = highlightStyle;
        if (hs != null && !hs.equals(new HighlightStyle())) {
            options.put("highlightStyle", mapper.convertValue(hs, Map.class));
        }
        if (voices != null && !voices.isEmpty()) options.put("voices", voices);
        if (debugOverlay) options.put("debugOverlay", true);
        if (fontSize != 24) options.put("fontSize", fontSize);
        if (!options.isEmpty()) root.put("options", options);
        String json = mapper
            .writerWithDefaultPrettyPrinter()
            .writeValueAsString(root);
        Files.writeString(outputDir.resolve("storyboard.json"), json);
    }
}
