
package screencastnarrator.generated;

import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * Schema for config.json — shared configuration for all clients.
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "recording",
    "highlight"
})
@Generated("jsonschema2pojo")
public class ConfigSchema {

    /**
     * CDP video recording settings shared across all clients.
     * (Required)
     * 
     */
    @JsonProperty("recording")
    @JsonPropertyDescription("CDP video recording settings shared across all clients.")
    private RecordingConfig recording;
    /**
     * Highlight drawing defaults loaded at runtime.
     * (Required)
     * 
     */
    @JsonProperty("highlight")
    @JsonPropertyDescription("Highlight drawing defaults loaded at runtime.")
    private HighlightConfig highlight;

    /**
     * No args constructor for use in serialization
     * 
     */
    public ConfigSchema() {
    }

    public ConfigSchema(RecordingConfig recording, HighlightConfig highlight) {
        super();
        this.recording = recording;
        this.highlight = highlight;
    }

    /**
     * CDP video recording settings shared across all clients.
     * (Required)
     * 
     */
    @JsonProperty("recording")
    public RecordingConfig getRecording() {
        return recording;
    }

    /**
     * CDP video recording settings shared across all clients.
     * (Required)
     * 
     */
    @JsonProperty("recording")
    public void setRecording(RecordingConfig recording) {
        this.recording = recording;
    }

    /**
     * Highlight drawing defaults loaded at runtime.
     * (Required)
     * 
     */
    @JsonProperty("highlight")
    public HighlightConfig getHighlight() {
        return highlight;
    }

    /**
     * Highlight drawing defaults loaded at runtime.
     * (Required)
     * 
     */
    @JsonProperty("highlight")
    public void setHighlight(HighlightConfig highlight) {
        this.highlight = highlight;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(ConfigSchema.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("recording");
        sb.append('=');
        sb.append(((this.recording == null)?"<null>":this.recording));
        sb.append(',');
        sb.append("highlight");
        sb.append('=');
        sb.append(((this.highlight == null)?"<null>":this.highlight));
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
        result = ((result* 31)+((this.recording == null)? 0 :this.recording.hashCode()));
        result = ((result* 31)+((this.highlight == null)? 0 :this.highlight.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof ConfigSchema) == false) {
            return false;
        }
        ConfigSchema rhs = ((ConfigSchema) other);
        return (((this.recording == rhs.recording)||((this.recording!= null)&&this.recording.equals(rhs.recording)))&&((this.highlight == rhs.highlight)||((this.highlight!= null)&&this.highlight.equals(rhs.highlight))));
    }

}
