package screencastnarrator;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import screencastnarrator.generated.ConfigSchema;
import screencastnarrator.generated.HighlightConfig;
import screencastnarrator.generated.HighlightStyle;
import screencastnarrator.generated.RecordingConfig;

public class SharedConfig {

    private static SharedConfig instance;

    private final RecordingConfig recording;
    private final HighlightConfig highlight;

    private SharedConfig(RecordingConfig recording, HighlightConfig highlight) {
        this.recording = recording;
        this.highlight = highlight;
    }

    public RecordingConfig recording() {
        return recording;
    }

    public HighlightConfig highlight() {
        return highlight;
    }

    public static SharedConfig load() {
        if (instance != null) {
            return instance;
        }
        try (InputStream is = SharedConfig.class.getResourceAsStream("/common/config.json")) {
            if (is == null) {
                throw new IllegalStateException("common/config.json not found on classpath");
            }
            ConfigSchema schema = new ObjectMapper().readValue(is, ConfigSchema.class);
            HighlightConfig hl = schema.getHighlight();
            hl.setScrollJs(resolveJs(hl.getScrollJs()));
            hl.setScrollWaitJs(resolveJs(hl.getScrollWaitJs()));
            hl.setDrawJs(resolveJs(hl.getDrawJs()));
            hl.setRemoveJs(resolveJs(hl.getRemoveJs()));
            instance = new SharedConfig(schema.getRecording(), hl);
            return instance;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public String resolvedDrawJs() {
        String result = highlight.getDrawJs();
        Map<String, Object> fields = new ObjectMapper().convertValue(highlight, Map.class);
        for (Map.Entry<String, Object> entry : fields.entrySet()) {
            result = result.replace("{{" + entry.getKey() + "}}", String.valueOf(entry.getValue()));
        }
        return result;
    }

    public List<String> ffmpegArgs(String outputFile) {
        RecordingConfig rec = recording;
        return List.of(
                "ffmpeg",
                "-loglevel", "error",
                "-f", "image2pipe",
                "-avioflags", "direct",
                "-fpsprobesize", "0",
                "-probesize", "32",
                "-analyzeduration", "0",
                "-c:v", "mjpeg",
                "-i", "pipe:0",
                "-y", "-an",
                "-r", String.valueOf(rec.getFps()),
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-c:v", rec.getCodec().value(),
                "-preset", rec.getPreset().value(),
                "-crf", String.valueOf(rec.getCrf()),
                "-pix_fmt", rec.getPixelFormat().value(),
                "-threads", "1",
                outputFile
        );
    }

    public SharedConfig withHighlightOverrides(HighlightStyle style) {
        HighlightConfig hl = highlight;
        HighlightConfig overridden = new HighlightConfig(
                style.getScrollWaitMs() != null ? style.getScrollWaitMs() : hl.getScrollWaitMs(),
                style.getDrawDurationMs() != null ? style.getDrawDurationMs() : hl.getDrawWaitMs(),
                style.getRemoveWaitMs() != null ? style.getRemoveWaitMs() : hl.getRemoveWaitMs(),
                style.getColor() != null ? style.getColor() : hl.getColor(),
                style.getPadding() != null ? style.getPadding() : hl.getPadding(),
                style.getAnimationSpeedMs() != null ? style.getAnimationSpeedMs() : hl.getAnimationSpeedMs(),
                style.getLineWidthMin() != null ? style.getLineWidthMin() : hl.getLineWidthMin(),
                style.getLineWidthMax() != null ? style.getLineWidthMax() : hl.getLineWidthMax(),
                style.getOpacity() != null ? style.getOpacity() : hl.getOpacity(),
                style.getSegments() != null ? style.getSegments() : hl.getSegments(),
                style.getCoverage() != null ? style.getCoverage() : hl.getCoverage(),
                hl.getScrollJs(),
                hl.getScrollWaitJs(),
                hl.getDrawJs(),
                hl.getRemoveJs()
        );
        return new SharedConfig(recording, overridden);
    }

    private static String resolveJs(String value) {
        if (!value.endsWith(".js")) return value;
        String resourcePath = "/common/" + value;
        try (InputStream js = SharedConfig.class.getResourceAsStream(resourcePath)) {
            if (js == null) return value;
            return new String(js.readAllBytes(), StandardCharsets.UTF_8).strip();
        } catch (IOException e) {
            return value;
        }
    }
}
