
package screencastnarrator.generated;

import java.util.HashMap;
import java.util.Map;
import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import com.fasterxml.jackson.annotation.JsonValue;


/**
 * CDP video recording settings shared across all clients.
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "fps",
    "jpegQuality",
    "minFrames",
    "minFrameWaitMs",
    "stopSettleMs",
    "codec",
    "preset",
    "crf",
    "pixelFormat"
})
@Generated("jsonschema2pojo")
public class RecordingConfig {

    /**
     * Target frames per second for video output
     * (Required)
     * 
     */
    @JsonProperty("fps")
    @JsonPropertyDescription("Target frames per second for video output")
    private Integer fps;
    /**
     * JPEG quality for CDP screencast frames
     * (Required)
     * 
     */
    @JsonProperty("jpegQuality")
    @JsonPropertyDescription("JPEG quality for CDP screencast frames")
    private Integer jpegQuality;
    /**
     * Minimum frames to capture before considering recording started
     * (Required)
     * 
     */
    @JsonProperty("minFrames")
    @JsonPropertyDescription("Minimum frames to capture before considering recording started")
    private Integer minFrames;
    /**
     * Polling interval in ms when waiting for minimum frames
     * (Required)
     * 
     */
    @JsonProperty("minFrameWaitMs")
    @JsonPropertyDescription("Polling interval in ms when waiting for minimum frames")
    private Integer minFrameWaitMs;
    /**
     * Settle time in ms after stopping the screencast before closing ffmpeg
     * (Required)
     * 
     */
    @JsonProperty("stopSettleMs")
    @JsonPropertyDescription("Settle time in ms after stopping the screencast before closing ffmpeg")
    private Integer stopSettleMs;
    /**
     * Video codec for ffmpeg output
     * (Required)
     * 
     */
    @JsonProperty("codec")
    @JsonPropertyDescription("Video codec for ffmpeg output")
    private RecordingConfig.Codec codec;
    /**
     * Encoding speed preset (faster = larger file, slower = smaller file)
     * (Required)
     * 
     */
    @JsonProperty("preset")
    @JsonPropertyDescription("Encoding speed preset (faster = larger file, slower = smaller file)")
    private RecordingConfig.Preset preset;
    /**
     * Constant rate factor (0 = lossless, 18 = visually lossless, 23 = default, 51 = worst)
     * (Required)
     * 
     */
    @JsonProperty("crf")
    @JsonPropertyDescription("Constant rate factor (0 = lossless, 18 = visually lossless, 23 = default, 51 = worst)")
    private Integer crf;
    /**
     * Pixel format for video output
     * (Required)
     * 
     */
    @JsonProperty("pixelFormat")
    @JsonPropertyDescription("Pixel format for video output")
    private RecordingConfig.PixelFormat pixelFormat;

    /**
     * No args constructor for use in serialization
     * 
     */
    public RecordingConfig() {
    }

    /**
     * 
     * @param codec
     *     Video codec for ffmpeg output.
     * @param jpegQuality
     *     JPEG quality for CDP screencast frames.
     * @param pixelFormat
     *     Pixel format for video output.
     * @param minFrameWaitMs
     *     Polling interval in ms when waiting for minimum frames.
     * @param stopSettleMs
     *     Settle time in ms after stopping the screencast before closing ffmpeg.
     * @param crf
     *     Constant rate factor (0 = lossless, 18 = visually lossless, 23 = default, 51 = worst).
     * @param fps
     *     Target frames per second for video output.
     * @param minFrames
     *     Minimum frames to capture before considering recording started.
     * @param preset
     *     Encoding speed preset (faster = larger file, slower = smaller file).
     */
    public RecordingConfig(Integer fps, Integer jpegQuality, Integer minFrames, Integer minFrameWaitMs, Integer stopSettleMs, RecordingConfig.Codec codec, RecordingConfig.Preset preset, Integer crf, RecordingConfig.PixelFormat pixelFormat) {
        super();
        this.fps = fps;
        this.jpegQuality = jpegQuality;
        this.minFrames = minFrames;
        this.minFrameWaitMs = minFrameWaitMs;
        this.stopSettleMs = stopSettleMs;
        this.codec = codec;
        this.preset = preset;
        this.crf = crf;
        this.pixelFormat = pixelFormat;
    }

    /**
     * Target frames per second for video output
     * (Required)
     * 
     */
    @JsonProperty("fps")
    public Integer getFps() {
        return fps;
    }

    /**
     * Target frames per second for video output
     * (Required)
     * 
     */
    @JsonProperty("fps")
    public void setFps(Integer fps) {
        this.fps = fps;
    }

    /**
     * JPEG quality for CDP screencast frames
     * (Required)
     * 
     */
    @JsonProperty("jpegQuality")
    public Integer getJpegQuality() {
        return jpegQuality;
    }

    /**
     * JPEG quality for CDP screencast frames
     * (Required)
     * 
     */
    @JsonProperty("jpegQuality")
    public void setJpegQuality(Integer jpegQuality) {
        this.jpegQuality = jpegQuality;
    }

    /**
     * Minimum frames to capture before considering recording started
     * (Required)
     * 
     */
    @JsonProperty("minFrames")
    public Integer getMinFrames() {
        return minFrames;
    }

    /**
     * Minimum frames to capture before considering recording started
     * (Required)
     * 
     */
    @JsonProperty("minFrames")
    public void setMinFrames(Integer minFrames) {
        this.minFrames = minFrames;
    }

    /**
     * Polling interval in ms when waiting for minimum frames
     * (Required)
     * 
     */
    @JsonProperty("minFrameWaitMs")
    public Integer getMinFrameWaitMs() {
        return minFrameWaitMs;
    }

    /**
     * Polling interval in ms when waiting for minimum frames
     * (Required)
     * 
     */
    @JsonProperty("minFrameWaitMs")
    public void setMinFrameWaitMs(Integer minFrameWaitMs) {
        this.minFrameWaitMs = minFrameWaitMs;
    }

    /**
     * Settle time in ms after stopping the screencast before closing ffmpeg
     * (Required)
     * 
     */
    @JsonProperty("stopSettleMs")
    public Integer getStopSettleMs() {
        return stopSettleMs;
    }

    /**
     * Settle time in ms after stopping the screencast before closing ffmpeg
     * (Required)
     * 
     */
    @JsonProperty("stopSettleMs")
    public void setStopSettleMs(Integer stopSettleMs) {
        this.stopSettleMs = stopSettleMs;
    }

    /**
     * Video codec for ffmpeg output
     * (Required)
     * 
     */
    @JsonProperty("codec")
    public RecordingConfig.Codec getCodec() {
        return codec;
    }

    /**
     * Video codec for ffmpeg output
     * (Required)
     * 
     */
    @JsonProperty("codec")
    public void setCodec(RecordingConfig.Codec codec) {
        this.codec = codec;
    }

    /**
     * Encoding speed preset (faster = larger file, slower = smaller file)
     * (Required)
     * 
     */
    @JsonProperty("preset")
    public RecordingConfig.Preset getPreset() {
        return preset;
    }

    /**
     * Encoding speed preset (faster = larger file, slower = smaller file)
     * (Required)
     * 
     */
    @JsonProperty("preset")
    public void setPreset(RecordingConfig.Preset preset) {
        this.preset = preset;
    }

    /**
     * Constant rate factor (0 = lossless, 18 = visually lossless, 23 = default, 51 = worst)
     * (Required)
     * 
     */
    @JsonProperty("crf")
    public Integer getCrf() {
        return crf;
    }

    /**
     * Constant rate factor (0 = lossless, 18 = visually lossless, 23 = default, 51 = worst)
     * (Required)
     * 
     */
    @JsonProperty("crf")
    public void setCrf(Integer crf) {
        this.crf = crf;
    }

    /**
     * Pixel format for video output
     * (Required)
     * 
     */
    @JsonProperty("pixelFormat")
    public RecordingConfig.PixelFormat getPixelFormat() {
        return pixelFormat;
    }

    /**
     * Pixel format for video output
     * (Required)
     * 
     */
    @JsonProperty("pixelFormat")
    public void setPixelFormat(RecordingConfig.PixelFormat pixelFormat) {
        this.pixelFormat = pixelFormat;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(RecordingConfig.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("fps");
        sb.append('=');
        sb.append(((this.fps == null)?"<null>":this.fps));
        sb.append(',');
        sb.append("jpegQuality");
        sb.append('=');
        sb.append(((this.jpegQuality == null)?"<null>":this.jpegQuality));
        sb.append(',');
        sb.append("minFrames");
        sb.append('=');
        sb.append(((this.minFrames == null)?"<null>":this.minFrames));
        sb.append(',');
        sb.append("minFrameWaitMs");
        sb.append('=');
        sb.append(((this.minFrameWaitMs == null)?"<null>":this.minFrameWaitMs));
        sb.append(',');
        sb.append("stopSettleMs");
        sb.append('=');
        sb.append(((this.stopSettleMs == null)?"<null>":this.stopSettleMs));
        sb.append(',');
        sb.append("codec");
        sb.append('=');
        sb.append(((this.codec == null)?"<null>":this.codec));
        sb.append(',');
        sb.append("preset");
        sb.append('=');
        sb.append(((this.preset == null)?"<null>":this.preset));
        sb.append(',');
        sb.append("crf");
        sb.append('=');
        sb.append(((this.crf == null)?"<null>":this.crf));
        sb.append(',');
        sb.append("pixelFormat");
        sb.append('=');
        sb.append(((this.pixelFormat == null)?"<null>":this.pixelFormat));
        sb.append(',');
        if (sb.charAt((sb.length()- 1)) == ',') {
            sb.setCharAt((sb.length()- 1), ']');
        } else {
            sb.append(']');
        }
        return sb.toString();
    }

    @Override
    public int hashCode() {
        int result = 1;
        result = ((result* 31)+((this.codec == null)? 0 :this.codec.hashCode()));
        result = ((result* 31)+((this.jpegQuality == null)? 0 :this.jpegQuality.hashCode()));
        result = ((result* 31)+((this.pixelFormat == null)? 0 :this.pixelFormat.hashCode()));
        result = ((result* 31)+((this.minFrameWaitMs == null)? 0 :this.minFrameWaitMs.hashCode()));
        result = ((result* 31)+((this.stopSettleMs == null)? 0 :this.stopSettleMs.hashCode()));
        result = ((result* 31)+((this.crf == null)? 0 :this.crf.hashCode()));
        result = ((result* 31)+((this.fps == null)? 0 :this.fps.hashCode()));
        result = ((result* 31)+((this.minFrames == null)? 0 :this.minFrames.hashCode()));
        result = ((result* 31)+((this.preset == null)? 0 :this.preset.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof RecordingConfig) == false) {
            return false;
        }
        RecordingConfig rhs = ((RecordingConfig) other);
        return ((((((((((this.codec == rhs.codec)||((this.codec!= null)&&this.codec.equals(rhs.codec)))&&((this.jpegQuality == rhs.jpegQuality)||((this.jpegQuality!= null)&&this.jpegQuality.equals(rhs.jpegQuality))))&&((this.pixelFormat == rhs.pixelFormat)||((this.pixelFormat!= null)&&this.pixelFormat.equals(rhs.pixelFormat))))&&((this.minFrameWaitMs == rhs.minFrameWaitMs)||((this.minFrameWaitMs!= null)&&this.minFrameWaitMs.equals(rhs.minFrameWaitMs))))&&((this.stopSettleMs == rhs.stopSettleMs)||((this.stopSettleMs!= null)&&this.stopSettleMs.equals(rhs.stopSettleMs))))&&((this.crf == rhs.crf)||((this.crf!= null)&&this.crf.equals(rhs.crf))))&&((this.fps == rhs.fps)||((this.fps!= null)&&this.fps.equals(rhs.fps))))&&((this.minFrames == rhs.minFrames)||((this.minFrames!= null)&&this.minFrames.equals(rhs.minFrames))))&&((this.preset == rhs.preset)||((this.preset!= null)&&this.preset.equals(rhs.preset))));
    }


    /**
     * Video codec for ffmpeg output
     * 
     */
    @Generated("jsonschema2pojo")
    public enum Codec {

        LIBX_264("libx264"),
        LIBX_265("libx265"),
        LIBVPX_VP_9("libvpx-vp9");
        private final String value;
        private final static Map<String, RecordingConfig.Codec> CONSTANTS = new HashMap<String, RecordingConfig.Codec>();

        static {
            for (RecordingConfig.Codec c: values()) {
                CONSTANTS.put(c.value, c);
            }
        }

        Codec(String value) {
            this.value = value;
        }

        @Override
        public String toString() {
            return this.value;
        }

        @JsonValue
        public String value() {
            return this.value;
        }

        @JsonCreator
        public static RecordingConfig.Codec fromValue(String value) {
            RecordingConfig.Codec constant = CONSTANTS.get(value);
            if (constant == null) {
                throw new IllegalArgumentException(value);
            } else {
                return constant;
            }
        }

    }


    /**
     * Pixel format for video output
     * 
     */
    @Generated("jsonschema2pojo")
    public enum PixelFormat {

        YUV_420_P("yuv420p"),
        YUV_444_P("yuv444p");
        private final String value;
        private final static Map<String, RecordingConfig.PixelFormat> CONSTANTS = new HashMap<String, RecordingConfig.PixelFormat>();

        static {
            for (RecordingConfig.PixelFormat c: values()) {
                CONSTANTS.put(c.value, c);
            }
        }

        PixelFormat(String value) {
            this.value = value;
        }

        @Override
        public String toString() {
            return this.value;
        }

        @JsonValue
        public String value() {
            return this.value;
        }

        @JsonCreator
        public static RecordingConfig.PixelFormat fromValue(String value) {
            RecordingConfig.PixelFormat constant = CONSTANTS.get(value);
            if (constant == null) {
                throw new IllegalArgumentException(value);
            } else {
                return constant;
            }
        }

    }


    /**
     * Encoding speed preset (faster = larger file, slower = smaller file)
     * 
     */
    @Generated("jsonschema2pojo")
    public enum Preset {

        ULTRAFAST("ultrafast"),
        SUPERFAST("superfast"),
        VERYFAST("veryfast"),
        FASTER("faster"),
        FAST("fast"),
        MEDIUM("medium"),
        SLOW("slow"),
        SLOWER("slower"),
        VERYSLOW("veryslow");
        private final String value;
        private final static Map<String, RecordingConfig.Preset> CONSTANTS = new HashMap<String, RecordingConfig.Preset>();

        static {
            for (RecordingConfig.Preset c: values()) {
                CONSTANTS.put(c.value, c);
            }
        }

        Preset(String value) {
            this.value = value;
        }

        @Override
        public String toString() {
            return this.value;
        }

        @JsonValue
        public String value() {
            return this.value;
        }

        @JsonCreator
        public static RecordingConfig.Preset fromValue(String value) {
            RecordingConfig.Preset constant = CONSTANTS.get(value);
            if (constant == null) {
                throw new IllegalArgumentException(value);
            } else {
                return constant;
            }
        }

    }

}
