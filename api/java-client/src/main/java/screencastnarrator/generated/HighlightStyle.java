
package screencastnarrator.generated;

import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * User-customizable highlight appearance. All fields are optional — unset fields inherit from the shared config defaults.
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "color",
    "animationSpeedMs",
    "drawDurationMs",
    "opacity",
    "padding"
})
@Generated("jsonschema2pojo")
public class HighlightStyle {

    /**
     * CSS color for the highlight stroke (e.g. '#ff0000')
     * 
     */
    @JsonProperty("color")
    @JsonPropertyDescription("CSS color for the highlight stroke (e.g. '#ff0000')")
    private String color;
    /**
     * Duration of the draw animation in milliseconds
     * 
     */
    @JsonProperty("animationSpeedMs")
    @JsonPropertyDescription("Duration of the draw animation in milliseconds")
    private Integer animationSpeedMs;
    /**
     * How long the highlight stays visible after drawing
     * 
     */
    @JsonProperty("drawDurationMs")
    @JsonPropertyDescription("How long the highlight stays visible after drawing")
    private Integer drawDurationMs;
    /**
     * Opacity of the highlight stroke
     * 
     */
    @JsonProperty("opacity")
    @JsonPropertyDescription("Opacity of the highlight stroke")
    private Double opacity;
    /**
     * Padding around the element bounding box
     * 
     */
    @JsonProperty("padding")
    @JsonPropertyDescription("Padding around the element bounding box")
    private Integer padding;

    /**
     * No args constructor for use in serialization
     * 
     */
    public HighlightStyle() {
    }

    /**
     * 
     * @param padding
     *     Padding around the element bounding box.
     * @param color
     *     CSS color for the highlight stroke (e.g. '#ff0000').
     * @param animationSpeedMs
     *     Duration of the draw animation in milliseconds.
     * @param opacity
     *     Opacity of the highlight stroke.
     * @param drawDurationMs
     *     How long the highlight stays visible after drawing.
     */
    public HighlightStyle(String color, Integer animationSpeedMs, Integer drawDurationMs, Double opacity, Integer padding) {
        super();
        this.color = color;
        this.animationSpeedMs = animationSpeedMs;
        this.drawDurationMs = drawDurationMs;
        this.opacity = opacity;
        this.padding = padding;
    }

    /**
     * CSS color for the highlight stroke (e.g. '#ff0000')
     * 
     */
    @JsonProperty("color")
    public String getColor() {
        return color;
    }

    /**
     * CSS color for the highlight stroke (e.g. '#ff0000')
     * 
     */
    @JsonProperty("color")
    public void setColor(String color) {
        this.color = color;
    }

    /**
     * Duration of the draw animation in milliseconds
     * 
     */
    @JsonProperty("animationSpeedMs")
    public Integer getAnimationSpeedMs() {
        return animationSpeedMs;
    }

    /**
     * Duration of the draw animation in milliseconds
     * 
     */
    @JsonProperty("animationSpeedMs")
    public void setAnimationSpeedMs(Integer animationSpeedMs) {
        this.animationSpeedMs = animationSpeedMs;
    }

    /**
     * How long the highlight stays visible after drawing
     * 
     */
    @JsonProperty("drawDurationMs")
    public Integer getDrawDurationMs() {
        return drawDurationMs;
    }

    /**
     * How long the highlight stays visible after drawing
     * 
     */
    @JsonProperty("drawDurationMs")
    public void setDrawDurationMs(Integer drawDurationMs) {
        this.drawDurationMs = drawDurationMs;
    }

    /**
     * Opacity of the highlight stroke
     * 
     */
    @JsonProperty("opacity")
    public Double getOpacity() {
        return opacity;
    }

    /**
     * Opacity of the highlight stroke
     * 
     */
    @JsonProperty("opacity")
    public void setOpacity(Double opacity) {
        this.opacity = opacity;
    }

    /**
     * Padding around the element bounding box
     * 
     */
    @JsonProperty("padding")
    public Integer getPadding() {
        return padding;
    }

    /**
     * Padding around the element bounding box
     * 
     */
    @JsonProperty("padding")
    public void setPadding(Integer padding) {
        this.padding = padding;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(HighlightStyle.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("color");
        sb.append('=');
        sb.append(((this.color == null)?"<null>":this.color));
        sb.append(',');
        sb.append("animationSpeedMs");
        sb.append('=');
        sb.append(((this.animationSpeedMs == null)?"<null>":this.animationSpeedMs));
        sb.append(',');
        sb.append("drawDurationMs");
        sb.append('=');
        sb.append(((this.drawDurationMs == null)?"<null>":this.drawDurationMs));
        sb.append(',');
        sb.append("opacity");
        sb.append('=');
        sb.append(((this.opacity == null)?"<null>":this.opacity));
        sb.append(',');
        sb.append("padding");
        sb.append('=');
        sb.append(((this.padding == null)?"<null>":this.padding));
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
        result = ((result* 31)+((this.padding == null)? 0 :this.padding.hashCode()));
        result = ((result* 31)+((this.color == null)? 0 :this.color.hashCode()));
        result = ((result* 31)+((this.opacity == null)? 0 :this.opacity.hashCode()));
        result = ((result* 31)+((this.drawDurationMs == null)? 0 :this.drawDurationMs.hashCode()));
        result = ((result* 31)+((this.animationSpeedMs == null)? 0 :this.animationSpeedMs.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof HighlightStyle) == false) {
            return false;
        }
        HighlightStyle rhs = ((HighlightStyle) other);
        return ((((((this.padding == rhs.padding)||((this.padding!= null)&&this.padding.equals(rhs.padding)))&&((this.color == rhs.color)||((this.color!= null)&&this.color.equals(rhs.color))))&&((this.opacity == rhs.opacity)||((this.opacity!= null)&&this.opacity.equals(rhs.opacity))))&&((this.drawDurationMs == rhs.drawDurationMs)||((this.drawDurationMs!= null)&&this.drawDurationMs.equals(rhs.drawDurationMs))))&&((this.animationSpeedMs == rhs.animationSpeedMs)||((this.animationSpeedMs!= null)&&this.animationSpeedMs.equals(rhs.animationSpeedMs))));
    }

}
