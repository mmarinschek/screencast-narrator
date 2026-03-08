
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

@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "type",
    "screenActionId",
    "description",
    "timing",
    "durationMs"
})
@Generated("jsonschema2pojo")
public class ScreenAction {

    /**
     * Type of screen action
     * (Required)
     * 
     */
    @JsonProperty("type")
    @JsonPropertyDescription("Type of screen action")
    private ScreenAction.ScreenActionType type;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("screenActionId")
    private Integer screenActionId;
    @JsonProperty("description")
    private String description;
    /**
     * Timing mode (default: casted)
     * 
     */
    @JsonProperty("timing")
    @JsonPropertyDescription("Timing mode (default: casted)")
    private ScreenAction.ScreenActionTiming timing;
    /**
     * Required when timing is 'timed'
     * 
     */
    @JsonProperty("durationMs")
    @JsonPropertyDescription("Required when timing is 'timed'")
    private Integer durationMs;

    /**
     * No args constructor for use in serialization
     * 
     */
    public ScreenAction() {
    }

    /**
     * 
     * @param durationMs
     *     Required when timing is 'timed'.
     */
    public ScreenAction(ScreenAction.ScreenActionType type, Integer screenActionId, String description, ScreenAction.ScreenActionTiming timing, Integer durationMs) {
        super();
        this.type = type;
        this.screenActionId = screenActionId;
        this.description = description;
        this.timing = timing;
        this.durationMs = durationMs;
    }

    /**
     * Type of screen action
     * (Required)
     * 
     */
    @JsonProperty("type")
    public ScreenAction.ScreenActionType getType() {
        return type;
    }

    /**
     * Type of screen action
     * (Required)
     * 
     */
    @JsonProperty("type")
    public void setType(ScreenAction.ScreenActionType type) {
        this.type = type;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("screenActionId")
    public Integer getScreenActionId() {
        return screenActionId;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("screenActionId")
    public void setScreenActionId(Integer screenActionId) {
        this.screenActionId = screenActionId;
    }

    @JsonProperty("description")
    public String getDescription() {
        return description;
    }

    @JsonProperty("description")
    public void setDescription(String description) {
        this.description = description;
    }

    /**
     * Timing mode (default: casted)
     * 
     */
    @JsonProperty("timing")
    public ScreenAction.ScreenActionTiming getTiming() {
        return timing;
    }

    /**
     * Timing mode (default: casted)
     * 
     */
    @JsonProperty("timing")
    public void setTiming(ScreenAction.ScreenActionTiming timing) {
        this.timing = timing;
    }

    /**
     * Required when timing is 'timed'
     * 
     */
    @JsonProperty("durationMs")
    public Integer getDurationMs() {
        return durationMs;
    }

    /**
     * Required when timing is 'timed'
     * 
     */
    @JsonProperty("durationMs")
    public void setDurationMs(Integer durationMs) {
        this.durationMs = durationMs;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(ScreenAction.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("type");
        sb.append('=');
        sb.append(((this.type == null)?"<null>":this.type));
        sb.append(',');
        sb.append("screenActionId");
        sb.append('=');
        sb.append(((this.screenActionId == null)?"<null>":this.screenActionId));
        sb.append(',');
        sb.append("description");
        sb.append('=');
        sb.append(((this.description == null)?"<null>":this.description));
        sb.append(',');
        sb.append("timing");
        sb.append('=');
        sb.append(((this.timing == null)?"<null>":this.timing));
        sb.append(',');
        sb.append("durationMs");
        sb.append('=');
        sb.append(((this.durationMs == null)?"<null>":this.durationMs));
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
        result = ((result* 31)+((this.description == null)? 0 :this.description.hashCode()));
        result = ((result* 31)+((this.screenActionId == null)? 0 :this.screenActionId.hashCode()));
        result = ((result* 31)+((this.type == null)? 0 :this.type.hashCode()));
        result = ((result* 31)+((this.durationMs == null)? 0 :this.durationMs.hashCode()));
        result = ((result* 31)+((this.timing == null)? 0 :this.timing.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof ScreenAction) == false) {
            return false;
        }
        ScreenAction rhs = ((ScreenAction) other);
        return ((((((this.description == rhs.description)||((this.description!= null)&&this.description.equals(rhs.description)))&&((this.screenActionId == rhs.screenActionId)||((this.screenActionId!= null)&&this.screenActionId.equals(rhs.screenActionId))))&&((this.type == rhs.type)||((this.type!= null)&&this.type.equals(rhs.type))))&&((this.durationMs == rhs.durationMs)||((this.durationMs!= null)&&this.durationMs.equals(rhs.durationMs))))&&((this.timing == rhs.timing)||((this.timing!= null)&&this.timing.equals(rhs.timing))));
    }


    /**
     * Timing mode (default: casted)
     * 
     */
    @Generated("jsonschema2pojo")
    public enum ScreenActionTiming {

        CASTED("casted"),
        ELASTIC("elastic"),
        TIMED("timed");
        private final String value;
        private final static Map<String, ScreenAction.ScreenActionTiming> CONSTANTS = new HashMap<String, ScreenAction.ScreenActionTiming>();

        static {
            for (ScreenAction.ScreenActionTiming c: values()) {
                CONSTANTS.put(c.value, c);
            }
        }

        ScreenActionTiming(String value) {
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
        public static ScreenAction.ScreenActionTiming fromValue(String value) {
            ScreenAction.ScreenActionTiming constant = CONSTANTS.get(value);
            if (constant == null) {
                throw new IllegalArgumentException(value);
            } else {
                return constant;
            }
        }

    }


    /**
     * Type of screen action
     * 
     */
    @Generated("jsonschema2pojo")
    public enum ScreenActionType {

        HIGHLIGHT("highlight"),
        NAVIGATE("navigate"),
        INPUT("input"),
        SCROLL("scroll"),
        WAIT("wait"),
        ANIMATE("animate"),
        TITLE("title");
        private final String value;
        private final static Map<String, ScreenAction.ScreenActionType> CONSTANTS = new HashMap<String, ScreenAction.ScreenActionType>();

        static {
            for (ScreenAction.ScreenActionType c: values()) {
                CONSTANTS.put(c.value, c);
            }
        }

        ScreenActionType(String value) {
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
        public static ScreenAction.ScreenActionType fromValue(String value) {
            ScreenAction.ScreenActionType constant = CONSTANTS.get(value);
            if (constant == null) {
                throw new IllegalArgumentException(value);
            } else {
                return constant;
            }
        }

    }

}
