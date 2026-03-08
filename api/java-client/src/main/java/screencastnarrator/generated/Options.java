
package screencastnarrator.generated;

import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "debugOverlay",
    "fontSize",
    "highlightStyle"
})
@Generated("jsonschema2pojo")
public class Options {

    @JsonProperty("debugOverlay")
    private Boolean debugOverlay;
    @JsonProperty("fontSize")
    private Integer fontSize;
    /**
     * User-customizable highlight appearance. All fields are optional — unset fields inherit from the shared config defaults.
     * 
     */
    @JsonProperty("highlightStyle")
    @JsonPropertyDescription("User-customizable highlight appearance. All fields are optional \u2014 unset fields inherit from the shared config defaults.")
    private HighlightStyle highlightStyle;

    /**
     * No args constructor for use in serialization
     * 
     */
    public Options() {
    }

    public Options(Boolean debugOverlay, Integer fontSize, HighlightStyle highlightStyle) {
        super();
        this.debugOverlay = debugOverlay;
        this.fontSize = fontSize;
        this.highlightStyle = highlightStyle;
    }

    @JsonProperty("debugOverlay")
    public Boolean getDebugOverlay() {
        return debugOverlay;
    }

    @JsonProperty("debugOverlay")
    public void setDebugOverlay(Boolean debugOverlay) {
        this.debugOverlay = debugOverlay;
    }

    @JsonProperty("fontSize")
    public Integer getFontSize() {
        return fontSize;
    }

    @JsonProperty("fontSize")
    public void setFontSize(Integer fontSize) {
        this.fontSize = fontSize;
    }

    /**
     * User-customizable highlight appearance. All fields are optional — unset fields inherit from the shared config defaults.
     * 
     */
    @JsonProperty("highlightStyle")
    public HighlightStyle getHighlightStyle() {
        return highlightStyle;
    }

    /**
     * User-customizable highlight appearance. All fields are optional — unset fields inherit from the shared config defaults.
     * 
     */
    @JsonProperty("highlightStyle")
    public void setHighlightStyle(HighlightStyle highlightStyle) {
        this.highlightStyle = highlightStyle;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(Options.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("debugOverlay");
        sb.append('=');
        sb.append(((this.debugOverlay == null)?"<null>":this.debugOverlay));
        sb.append(',');
        sb.append("fontSize");
        sb.append('=');
        sb.append(((this.fontSize == null)?"<null>":this.fontSize));
        sb.append(',');
        sb.append("highlightStyle");
        sb.append('=');
        sb.append(((this.highlightStyle == null)?"<null>":this.highlightStyle));
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
        result = ((result* 31)+((this.debugOverlay == null)? 0 :this.debugOverlay.hashCode()));
        result = ((result* 31)+((this.fontSize == null)? 0 :this.fontSize.hashCode()));
        result = ((result* 31)+((this.highlightStyle == null)? 0 :this.highlightStyle.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof Options) == false) {
            return false;
        }
        Options rhs = ((Options) other);
        return ((((this.debugOverlay == rhs.debugOverlay)||((this.debugOverlay!= null)&&this.debugOverlay.equals(rhs.debugOverlay)))&&((this.fontSize == rhs.fontSize)||((this.fontSize!= null)&&this.fontSize.equals(rhs.fontSize))))&&((this.highlightStyle == rhs.highlightStyle)||((this.highlightStyle!= null)&&this.highlightStyle.equals(rhs.highlightStyle))));
    }

}
