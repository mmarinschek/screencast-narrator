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

import screencastnarrator.generated.HighlightStyle;
import screencastnarrator.generated.SyncFrameStyle;

public class Storyboard {

    @FunctionalInterface
    public interface Action {
        void execute(Storyboard storyboard) throws Exception;
    }

    private final SharedConfig config;
    private final SharedConfig.SyncMarkers sm;
    private final SyncFrames syncFrames;
    private final Path outputDir;
    private final Page page;
    private final String language;
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
    private SyncFrameStyle syncFrameStyle;
    private Map<String, Map<String, String>> voices;

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle, SyncFrameStyle syncFrameStyle, Map<String, Map<String, String>> voices) throws Exception {
        this.config = SharedConfig.load();
        this.sm = config.syncMarkers();
        this.outputDir = outputDir;
        this.page = page;
        this.language = language;
        this.highlightStyle = highlightStyle != null ? highlightStyle : new HighlightStyle();
        this.syncFrameStyle = syncFrameStyle != null ? syncFrameStyle : new SyncFrameStyle();
        this.voices = voices;
        SharedConfig.SyncFrameConfig overriddenSyncFrameConfig = SyncFrameStyles.applyTo(this.syncFrameStyle, config.syncFrame());
        this.syncFrames = new SyncFrames(config, overriddenSyncFrameConfig);
        Files.createDirectories(outputDir);
        injectInitFrame();
    }

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle, SyncFrameStyle syncFrameStyle) throws Exception {
        this(outputDir, page, language, highlightStyle, syncFrameStyle, null);
    }

    public Storyboard(Path outputDir, Page page, String language, HighlightStyle highlightStyle) throws Exception {
        this(outputDir, page, language, highlightStyle, null, null);
    }

    public Storyboard(Path outputDir, Page page, String language) throws Exception {
        this(outputDir, page, language, null, null, null);
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

    public SyncFrameStyle getSyncFrameStyle() {
        return syncFrameStyle;
    }

    public Storyboard withHighlightStyle(HighlightStyle style) {
        this.highlightStyle = HighlightStyles.merge(this.highlightStyle, style);
        return this;
    }

    public Storyboard withSyncFrameStyle(SyncFrameStyle style) {
        this.syncFrameStyle = SyncFrameStyles.merge(this.syncFrameStyle, style);
        return this;
    }

    private boolean isDebugOverlay() {
        Boolean val = syncFrameStyle.getDebugOverlay();
        return val != null && val;
    }

    private int getFontSize() {
        Integer val = syncFrameStyle.getFontSize();
        return val != null ? val : 24;
    }

    private void injectInitFrame() throws Exception {
        if (page == null) return;
        syncFrames.injectInitFrame(page, language, isDebugOverlay(), getFontSize(), voices);
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
        Map<String, String> tr = pendingTranslations.isEmpty() ? null : new LinkedHashMap<>(pendingTranslations);
        injectSyncFrame(nid, sm.start(), text != null ? text : "", tr, voice);
        return nid;
    }

    public int beginScreenAction(String description) throws Exception {
        return beginScreenAction(description, "casted", null);
    }

    public int beginScreenAction() throws Exception {
        return beginScreenAction(null, "casted", null);
    }

    public int beginScreenAction(String description, String timing, Integer durationMs) throws Exception {
        if (!narrationOpen) {
            throw new IllegalStateException(
                "Cannot begin a screen action outside of a narration bracket");
        }
        if (pendingActionId != null) {
            throw new IllegalStateException(
                "Cannot begin a new screen action while another is still open");
        }
        if ("timed".equals(timing) && durationMs == null) {
            throw new IllegalArgumentException(
                "durationMs is required when timing is 'timed'");
        }
        int said = screenActionIdCounter++;
        Map<String, Object> action = new LinkedHashMap<>();
        action.put("screenActionId", said);
        if (description != null) {
            action.put("description", description);
        }
        if (timing != null && !"casted".equals(timing)) {
            action.put("timing", timing);
        }
        if (durationMs != null) {
            action.put("durationMs", durationMs);
        }
        pendingScreenActions.add(action);
        pendingActionId = said;
        String timingStr = (timing != null && !"casted".equals(timing)) ? timing : null;
        injectActionSyncFrame(said, sm.start(), description, timingStr, durationMs);
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
        SharedConfig.HighlightConfig hlConfig = HighlightStyles.applyTo(highlightStyle, config.highlight());
        injectHighlightSyncFrame(hid, sm.start());
        Highlight.highlight(page, locator, hlConfig);
        injectHighlightSyncFrame(hid, sm.end());
        Map<String, Object> hl = new LinkedHashMap<>();
        hl.put("highlightId", hid);
        pendingHighlights.add(hl);
    }

    public void done() throws Exception {
        if (narrationOpen) {
            throw new IllegalStateException("Cannot finalize: a narration bracket is still open");
        }
        if (page == null) return;
        syncFrames.injectDoneFrame(page);
    }

    public void endScreenAction() throws Exception {
        if (pendingActionId == null) {
            throw new IllegalStateException(
                "Cannot end screen action: no screen action is open");
        }
        injectActionSyncFrame(pendingActionId, sm.end());
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
        injectSyncFrame(pendingNarrationId, sm.end());
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
        return screenAction(null, "casted", null, action);
    }

    public int screenAction(String description, Action action) throws Exception {
        return screenAction(description, "casted", null, action);
    }

    public int screenAction(String description, String timing, Integer durationMs, Action action) throws Exception {
        int said = beginScreenAction(description, timing, durationMs);
        try {
            action.execute(this);
        } finally {
            endScreenAction();
        }
        return said;
    }

    private void injectSyncFrame(int narrationId, MarkerPosition marker) throws Exception {
        injectSyncFrame(narrationId, marker, "", null, null);
    }

    private void injectSyncFrame(int narrationId, MarkerPosition marker, String text,
                                 Map<String, String> translations, String voice) throws Exception {
        if (page == null) return;
        syncFrames.injectSyncFrame(page, narrationId, marker, text, translations, voice);
    }

    private void injectActionSyncFrame(int actionId, MarkerPosition marker) throws Exception {
        injectActionSyncFrame(actionId, marker, null, null, null);
    }

    private void injectActionSyncFrame(int actionId, MarkerPosition marker, String description, String timing, Integer durationMs) throws Exception {
        if (page == null) return;
        syncFrames.injectActionSyncFrame(page, actionId, marker, description, timing, durationMs);
    }

    private void injectHighlightSyncFrame(int highlightId, MarkerPosition marker) throws Exception {
        if (page == null) return;
        syncFrames.injectHighlightSyncFrame(page, highlightId, marker);
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
        SyncFrameStyle sfs = syncFrameStyle;
        if (sfs != null && !sfs.equals(new SyncFrameStyle())) {
            options.put("syncFrameStyle", mapper.convertValue(sfs, Map.class));
        }
        if (voices != null && !voices.isEmpty()) options.put("voices", voices);
        if (!options.isEmpty()) root.put("options", options);
        String json = mapper
            .writerWithDefaultPrettyPrinter()
            .writeValueAsString(root);
        Files.writeString(outputDir.resolve("storyboard.json"), json);
    }
}
