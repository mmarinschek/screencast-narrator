package screencastnarrator;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class StoryboardTest {

    private final ObjectMapper mapper = new ObjectMapper();

    private JsonNode readStoryboard(Path dir) throws Exception {
        return mapper.readTree(Files.readString(dir.resolve("storyboard.json")));
    }

    @Test
    void createsNarrationEntryWithText(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("Hello world");
        sb.endNarration();

        JsonNode data = readStoryboard(dir);
        JsonNode narrations = data.get("narrations");
        assertEquals(1, narrations.size());
        assertEquals(0, narrations.get(0).get("narrationId").asInt());
        assertEquals("Hello world", narrations.get(0).get("text").asText());
    }

    @Test
    void autoIncrementsNarrationIds(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("First");
        sb.endNarration();
        sb.beginNarration("Second");
        sb.endNarration();

        JsonNode narrations = readStoryboard(dir).get("narrations");
        assertEquals(0, narrations.get(0).get("narrationId").asInt());
        assertEquals(1, narrations.get(1).get("narrationId").asInt());
    }

    @Test
    void storesVoiceOnNarration(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir, null, "en", null, false, 24,
                Map.of("douglas", Map.of("en", "am_adam")));
        sb.beginNarration("Hello", Map.of(), "douglas");
        sb.endNarration();

        JsonNode narration = readStoryboard(dir).get("narrations").get(0);
        assertEquals("douglas", narration.get("voice").asText());
    }

    @Test
    void omitsVoiceWhenNotSpecified(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("Hello");
        sb.endNarration();

        JsonNode narration = readStoryboard(dir).get("narrations").get(0);
        assertNull(narration.get("voice"));
    }

    @Test
    void storesTranslationsOnNarration(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("Hello", Map.of("de", "Hallo"));
        sb.endNarration();

        JsonNode narration = readStoryboard(dir).get("narrations").get(0);
        assertEquals("Hallo", narration.get("translations").get("de").asText());
    }

    @Test
    void includesVideoFilePathOnNarration(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("Hello");
        sb.endNarration();

        JsonNode narration = readStoryboard(dir).get("narrations").get(0);
        assertEquals("videos/narration-000.mp4", narration.get("videoFile").asText());
    }

    @Test
    void includesVoicesInOptions(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir, null, "en", null, false, 24,
                Map.of("douglas", Map.of("en", "am_adam"),
                       "natalie", Map.of("en", "bf_alice")));
        sb.beginNarration("Hello", Map.of(), "douglas");
        sb.endNarration();

        JsonNode options = readStoryboard(dir).get("options");
        assertEquals("am_adam", options.get("voices").get("douglas").get("en").asText());
        assertEquals("bf_alice", options.get("voices").get("natalie").get("en").asText());
    }

    @Test
    void throwsWhenNestedNarrations(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("First");

        assertThrows(IllegalStateException.class, () -> sb.beginNarration("Second"));
    }

    @Test
    void doneSucceedsAfterAllNarrationsClosed(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("Hello");
        sb.endNarration();

        assertDoesNotThrow(sb::done);
    }

    @Test
    void doneThrowsIfNarrationIsOpen(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("Hello");

        assertThrows(IllegalStateException.class, sb::done);
    }

    @Test
    void debugOverlayAndFontSizeInOptions(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir, null, "en", null, true, 48);
        sb.beginNarration("Test");
        sb.endNarration();

        JsonNode options = readStoryboard(dir).get("options");
        assertTrue(options.get("debugOverlay").asBoolean());
        assertEquals(48, options.get("fontSize").asInt());
    }

    @Test
    void noOptionsWhenDefaults(@TempDir Path dir) throws Exception {
        Storyboard sb = new Storyboard(dir);
        sb.beginNarration("Test");
        sb.endNarration();

        assertNull(readStoryboard(dir).get("options"));
    }
}
