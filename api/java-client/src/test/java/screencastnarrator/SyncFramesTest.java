package screencastnarrator;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class SyncFramesTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final SharedConfig CONFIG = SharedConfig.load();
    private static final SyncFrames SYNC = new SyncFrames(CONFIG);

    @Test
    void syncFrame_withVoice_includesVcField() throws Exception {
        var page = (com.microsoft.playwright.Page) null;
        var payload = formatNarrationPayload(0, MarkerPosition.START, "Hello", null, "douglas");
        var parsed = MAPPER.readTree(payload);

        assertEquals("Hello", parsed.get("tx").asText());
        assertEquals("douglas", parsed.get("vc").asText());
    }

    @Test
    void syncFrame_withoutVoice_omitsVcField() throws Exception {
        var payload = formatNarrationPayload(0, MarkerPosition.START, "Hello", null, null);
        var parsed = MAPPER.readTree(payload);

        assertEquals("Hello", parsed.get("tx").asText());
        assertNull(parsed.get("vc"));
    }

    @Test
    void initFrame_withVoices_includesVoicesField() throws Exception {
        var voices = Map.of("douglas", Map.of("en", "am_adam"), "natalie", Map.of("en", "bf_alice"));
        var payload = formatInitPayload("en", false, 24, voices);
        var parsed = MAPPER.readTree(payload);

        assertNotNull(parsed.get("voices"));
        assertEquals("am_adam", parsed.get("voices").get("douglas").get("en").asText());
        assertEquals("bf_alice", parsed.get("voices").get("natalie").get("en").asText());
    }

    @Test
    void initFrame_withoutVoices_omitsVoicesField() throws Exception {
        var payload = formatInitPayload("en", false, 24, null);
        var parsed = MAPPER.readTree(payload);

        assertNull(parsed.get("voices"));
    }

    @Test
    void syncFrame_withTranslationsAndVoice_includesAll() throws Exception {
        var translations = Map.of("de", "Hallo");
        var payload = formatNarrationPayload(0, MarkerPosition.START, "Hello", translations, "harmony");
        var parsed = MAPPER.readTree(payload);

        assertEquals("Hello", parsed.get("tx").asText());
        assertEquals("Hallo", parsed.get("tr").get("de").asText());
        assertEquals("harmony", parsed.get("vc").asText());
    }

    @Test
    void splitIntoContinuationFrames_smallPayload_singleFrame() throws Exception {
        var payload = formatNarrationPayload(0, MarkerPosition.START, "short", null, "douglas");
        var frames = SYNC.splitIntoContinuationFrames(payload);
        assertEquals(1, frames.size());
        assertEquals(payload, frames.get(0));
    }

    private String formatNarrationPayload(int narrationId, MarkerPosition marker, String text,
                                           Map<String, String> translations, String voice) throws Exception {
        var sm = CONFIG.syncMarkers();
        var payload = new java.util.LinkedHashMap<String, Object>();
        payload.put("t", sm.narration().value());
        payload.put("id", narrationId);
        payload.put("m", marker.value());
        if (text != null && !text.isEmpty()) payload.put("tx", text);
        if (translations != null && !translations.isEmpty()) payload.put("tr", translations);
        if (voice != null && !voice.isEmpty()) payload.put("vc", voice);
        return MAPPER.writeValueAsString(payload);
    }

    private String formatInitPayload(String language, boolean debugOverlay, int fontSize,
                                      Map<String, Map<String, String>> voices) throws Exception {
        var sm = CONFIG.syncMarkers();
        var payload = new java.util.LinkedHashMap<String, Object>();
        payload.put("t", sm.init().value());
        payload.put("language", language);
        if (debugOverlay) payload.put("debugOverlay", true);
        if (fontSize != 24) payload.put("fontSize", fontSize);
        if (voices != null && !voices.isEmpty()) payload.put("voices", voices);
        return MAPPER.writeValueAsString(payload);
    }
}
