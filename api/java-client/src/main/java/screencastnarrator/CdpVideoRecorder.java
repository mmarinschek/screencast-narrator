package screencastnarrator;

import com.google.gson.JsonObject;
import com.microsoft.playwright.CDPSession;
import com.microsoft.playwright.Page;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Logger;

import screencastnarrator.generated.RecordingConfig;

public class CdpVideoRecorder {

    private static final Logger LOG = Logger.getLogger(CdpVideoRecorder.class.getName());

    private final Page page;
    private final Path outputFile;
    private final int width;
    private final int height;
    private final SharedConfig config;

    private CDPSession cdpSession;
    private Process ffmpegProcess;
    private OutputStream ffmpegStdin;
    private final AtomicBoolean recording = new AtomicBoolean(false);
    private volatile int frameCount;
    private volatile int lastSessionId = -1;

    public CdpVideoRecorder(Page page, Path outputFile, int width, int height, SharedConfig config) {
        this.page = page;
        this.outputFile = outputFile;
        this.width = width;
        this.height = height;
        this.config = config;
    }

    public void start() throws IOException {
        Files.createDirectories(outputFile.getParent());
        RecordingConfig rec = config.recording();

        List<String> args = config.ffmpegArgs(outputFile.toString());
        ProcessBuilder pb = new ProcessBuilder(args);
        pb.redirectErrorStream(true);
        ffmpegProcess = pb.start();
        ffmpegStdin = ffmpegProcess.getOutputStream();

        cdpSession = page.context().newCDPSession(page);

        recording.set(true);
        frameCount = 0;

        cdpSession.on("Page.screencastFrame", event -> {
            if (!recording.get()) return;
            try {
                String data = event.getAsJsonObject().get("data").getAsString();
                int sessionId = event.getAsJsonObject().get("sessionId").getAsInt();

                byte[] frameBytes = Base64.getDecoder().decode(data);
                synchronized (ffmpegStdin) {
                    ffmpegStdin.write(frameBytes);
                    ffmpegStdin.flush();
                }
                frameCount++;
                lastSessionId = sessionId;
            } catch (Exception e) {
                if (recording.get()) {
                    LOG.warning("Error processing screencast frame: " + e.getMessage());
                }
            }
        });

        JsonObject startParams = new JsonObject();
        startParams.addProperty("format", "jpeg");
        startParams.addProperty("quality", rec.getJpegQuality());
        startParams.addProperty("maxWidth", width);
        startParams.addProperty("maxHeight", height);
        startParams.addProperty("everyNthFrame", 1);
        cdpSession.send("Page.startScreencast", startParams);

        waitForMinFrames();

        LOG.info(String.format("CDP screencast recording started: %s (%dx%d, %d initial frames)",
                outputFile, width, height, frameCount));
    }

    void ackLatestFrame() {
        int sid = lastSessionId;
        if (sid >= 0) {
            JsonObject ackParams = new JsonObject();
            ackParams.addProperty("sessionId", sid);
            cdpSession.send("Page.screencastFrameAck", ackParams);
        }
    }

    private void waitForMinFrames() {
        RecordingConfig rec = config.recording();
        int maxWaits = 50;
        for (int i = 0; i < maxWaits && frameCount < rec.getMinFrames(); i++) {
            page.waitForTimeout(rec.getMinFrameWaitMs());
            ackLatestFrame();
        }
        if (frameCount < 1) {
            throw new RuntimeException("CDP screencast: no frames received after " + (maxWaits * rec.getMinFrameWaitMs()) + "ms");
        }
    }

    public void stop() throws IOException, InterruptedException {
        if (!recording.get()) return;
        RecordingConfig rec = config.recording();

        if (frameCount < rec.getMinFrames()) {
            int waits = (rec.getMinFrames() - frameCount) * 2;
            for (int i = 0; i < waits && frameCount < rec.getMinFrames(); i++) {
                page.waitForTimeout(rec.getMinFrameWaitMs());
            }
        }

        recording.set(false);
        cdpSession.send("Page.stopScreencast");

        page.waitForTimeout(rec.getStopSettleMs());

        synchronized (ffmpegStdin) {
            ffmpegStdin.close();
        }

        boolean exited = ffmpegProcess.waitFor(30, TimeUnit.SECONDS);
        if (!exited) {
            ffmpegProcess.destroyForcibly();
            throw new RuntimeException("ffmpeg did not exit within 30 seconds");
        }

        int exitCode = ffmpegProcess.exitValue();
        if (exitCode != 0) {
            String output = new String(ffmpegProcess.getInputStream().readAllBytes());
            throw new RuntimeException(String.format(
                    "ffmpeg exited with code %d (frames=%d): %s", exitCode, frameCount, output));
        }

        cdpSession.detach();
        LOG.info(String.format("CDP screencast recording stopped: %s (%d frames captured)", outputFile, frameCount));
    }

    public int getFrameCount() {
        return frameCount;
    }

    public Path getOutputFile() {
        return outputFile;
    }
}
