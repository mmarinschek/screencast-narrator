package screencastnarrator;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;

public record SharedConfig(SyncMarkers syncMarkers, SyncFrameConfig syncFrame, HighlightConfig highlight) {

    private static SharedConfig instance;

    public static SharedConfig load() {
        if (instance != null) {
            return instance;
        }
        try (InputStream is = SharedConfig.class.getResourceAsStream("/common/config.json")) {
            if (is == null) {
                throw new IllegalStateException(
                        "common/config.json not found on classpath");
            }
            JsonNode root = new ObjectMapper().readTree(is);
            instance = parse(root);
            return instance;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String resolveJs(String value) {
        if (!value.endsWith(".js")) return value;
        String resourcePath = "/common/" + value;
        try (InputStream js = SharedConfig.class.getResourceAsStream(resourcePath)) {
            if (js == null) return value;
            return new String(js.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8).strip();
        } catch (IOException e) {
            return value;
        }
    }

    private static SharedConfig parse(JsonNode root) {
        JsonNode smNode = root.get("syncMarkers");
        JsonNode sf = root.get("syncFrame");
        JsonNode hl = root.get("highlight");

        SyncMarkers syncMarkers = new SyncMarkers(
                SyncType.INIT,
                SyncType.NARRATION,
                SyncType.ACTION,
                SyncType.HIGHLIGHT,
                smNode.get("separator").asText(),
                MarkerPosition.START,
                MarkerPosition.END
        );

        SyncFrameConfig syncFrame = new SyncFrameConfig(
                sf.get("qrSize").asInt(),
                sf.get("displayDurationMs").asInt(),
                sf.get("postRemovalGapMs").asInt(),
                resolveJs(sf.get("injectJs").asText()),
                resolveJs(sf.get("removeJs").asText())
        );

        HighlightConfig highlight = new HighlightConfig(
                hl.get("scrollWaitMs").asInt(),
                hl.get("drawWaitMs").asInt(),
                hl.get("removeWaitMs").asInt(),
                hl.get("color").asText(),
                hl.get("padding").asInt(),
                hl.get("animationSpeedMs").asInt(),
                hl.get("lineWidthMin").asInt(),
                hl.get("lineWidthMax").asInt(),
                hl.get("opacity").asDouble(),
                hl.get("segments").asInt(),
                hl.get("coverage").asDouble(),
                resolveJs(hl.get("scrollJs").asText()),
                resolveJs(hl.get("scrollWaitJs").asText()),
                resolveJs(hl.get("drawJs").asText()),
                resolveJs(hl.get("removeJs").asText())
        );

        return new SharedConfig(syncMarkers, syncFrame, highlight);
    }

    public record SyncMarkers(
            SyncType init,
            SyncType narration,
            SyncType action,
            SyncType highlight,
            String separator,
            MarkerPosition start,
            MarkerPosition end
    ) {
        public String key(SyncType syncType, int entityId, MarkerPosition marker) {
            return syncType.value() + separator + entityId + separator + marker.value();
        }

        public String narrationStart(int narrationId) {
            return key(narration, narrationId, start);
        }

        public String narrationEnd(int narrationId) {
            return key(narration, narrationId, end);
        }

        public String actionStart(int actionId) {
            return key(action, actionId, start);
        }

        public String actionEnd(int actionId) {
            return key(action, actionId, end);
        }

        public String highlightStart(int highlightId) {
            return key(highlight, highlightId, start);
        }

        public String highlightEnd(int highlightId) {
            return key(highlight, highlightId, end);
        }
    }

    public record SyncFrameConfig(
            int qrSize,
            int displayDurationMs,
            int postRemovalGapMs,
            String injectJs,
            String removeJs
    ) {}

    public record HighlightConfig(
            int scrollWaitMs,
            int drawWaitMs,
            int removeWaitMs,
            String color,
            int padding,
            int animationSpeedMs,
            int lineWidthMin,
            int lineWidthMax,
            double opacity,
            int segments,
            double coverage,
            String scrollJs,
            String scrollWaitJs,
            String drawJs,
            String removeJs
    ) {
        public String resolvedDrawJs() {
            return drawJs
                    .replace("{{padding}}", String.valueOf(padding))
                    .replace("{{lineWidthMin}}", String.valueOf(lineWidthMin))
                    .replace("{{lineWidthMax}}", String.valueOf(lineWidthMax))
                    .replace("{{opacity}}", String.valueOf(opacity))
                    .replace("{{segments}}", String.valueOf(segments))
                    .replace("{{coverage}}", String.valueOf(coverage))
                    .replace("{{animationSpeedMs}}", String.valueOf(animationSpeedMs))
                    .replace("{{color}}", color);
        }
    }
}
