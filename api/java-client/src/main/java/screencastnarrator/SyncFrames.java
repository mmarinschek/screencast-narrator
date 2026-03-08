package screencastnarrator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;
import com.microsoft.playwright.Page;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class SyncFrames {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final int MAX_QR_DATA_LENGTH = 2000;

    private final SharedConfig.SyncFrameConfig syncFrameConfig;
    private final SharedConfig.SyncMarkers syncMarkers;

    public SyncFrames(SharedConfig config) {
        this.syncFrameConfig = config.syncFrame();
        this.syncMarkers = config.syncMarkers();
    }

    public void injectInitFrame(Page page, String language, boolean debugOverlay, int fontSize) throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("t", syncMarkers.init().value());
        payload.put("language", language);
        if (debugOverlay) payload.put("debugOverlay", true);
        if (fontSize != 24) payload.put("fontSize", fontSize);
        injectQrOverlay(page, MAPPER.writeValueAsString(payload));
    }

    public void injectSyncFrame(Page page, int narrationId, MarkerPosition marker) throws Exception {
        injectSyncFrame(page, narrationId, marker, "", null);
    }

    public void injectSyncFrame(Page page, int narrationId, MarkerPosition marker, String text) throws Exception {
        injectSyncFrame(page, narrationId, marker, text, null);
    }

    public void injectSyncFrame(Page page, int narrationId, MarkerPosition marker, String text, Map<String, String> translations) throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("t", syncMarkers.narration().value());
        payload.put("id", narrationId);
        payload.put("m", marker.value());
        if (text != null && !text.isEmpty()) payload.put("tx", text);
        if (translations != null && !translations.isEmpty()) payload.put("tr", translations);
        injectQrOverlay(page, MAPPER.writeValueAsString(payload));
    }

    public void injectActionSyncFrame(Page page, int actionId, MarkerPosition marker) throws Exception {
        injectActionSyncFrame(page, actionId, marker, null, null, null);
    }

    public void injectActionSyncFrame(Page page, int actionId, MarkerPosition marker,
                                       String description, String timing, Integer durationMs) throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("t", syncMarkers.action().value());
        payload.put("id", actionId);
        payload.put("m", marker.value());
        if (description != null) payload.put("desc", description);
        if (timing != null && !"casted".equals(timing)) payload.put("tm", timing);
        if (durationMs != null) payload.put("dur", durationMs);
        injectQrOverlay(page, MAPPER.writeValueAsString(payload));
    }

    public void injectHighlightSyncFrame(Page page, int highlightId, MarkerPosition marker) throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("t", syncMarkers.highlight().value());
        payload.put("id", highlightId);
        payload.put("m", marker.value());
        injectQrOverlay(page, MAPPER.writeValueAsString(payload));
    }

    private void injectQrOverlay(Page page, String data) throws Exception {
        List<String> frames = splitIntoContinuationFrames(data);
        for (String frame : frames) {
            injectSingleQr(page, frame);
        }
    }

    List<String> splitIntoContinuationFrames(String data) throws Exception {
        List<String> frames = new ArrayList<>();
        if (data.length() <= MAX_QR_DATA_LENGTH) {
            frames.add(data);
            return frames;
        }
        int chunkSize = MAX_QR_DATA_LENGTH - 30;
        for (int attempt = 0; attempt < 20; attempt++) {
            int total = (int) Math.ceil((double) data.length() / chunkSize);
            String testChunk = data.substring(0, Math.min(chunkSize, data.length()));
            Map<String, Object> wrapper = new LinkedHashMap<>();
            wrapper.put("_c", new int[]{0, total});
            wrapper.put("d", testChunk);
            if (MAPPER.writeValueAsString(wrapper).length() <= MAX_QR_DATA_LENGTH) break;
            chunkSize -= 50;
        }
        int total = (int) Math.ceil((double) data.length() / chunkSize);
        for (int i = 0; i < total; i++) {
            int start = i * chunkSize;
            int end = Math.min(start + chunkSize, data.length());
            String chunk = data.substring(start, end);
            Map<String, Object> wrapper = new LinkedHashMap<>();
            wrapper.put("_c", new int[]{i, total});
            wrapper.put("d", chunk);
            frames.add(MAPPER.writeValueAsString(wrapper));
        }
        return frames;
    }

    private void injectSingleQr(Page page, String data) throws Exception {
        String dataUrl = generateQrDataUrl(data);
        String js = syncFrameConfig.injectJs().replace("{{dataUrl}}", dataUrl);
        page.evaluate(js);
        page.waitForTimeout(syncFrameConfig.displayDurationMs());
        page.evaluate(syncFrameConfig.removeJs());
        page.waitForTimeout(syncFrameConfig.postRemovalGapMs());
    }

    private String generateQrDataUrl(String data) throws Exception {
        int qrSize = syncFrameConfig.qrSize();
        QRCodeWriter writer = new QRCodeWriter();
        BitMatrix matrix = writer.encode(data, BarcodeFormat.QR_CODE, qrSize, qrSize);
        BufferedImage image = new BufferedImage(qrSize, qrSize, BufferedImage.TYPE_INT_RGB);
        for (int x = 0; x < qrSize; x++) {
            for (int y = 0; y < qrSize; y++) {
                image.setRGB(x, y, matrix.get(x, y) ? 0x000000 : 0xFFFFFF);
            }
        }
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "PNG", baos);
        String b64 = Base64.getEncoder().encodeToString(baos.toByteArray());
        return "data:image/png;base64," + b64;
    }
}
