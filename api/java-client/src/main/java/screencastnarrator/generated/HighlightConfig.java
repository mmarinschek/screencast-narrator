
package screencastnarrator.generated;

import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * Highlight drawing defaults loaded at runtime.
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "scrollWaitMs",
    "drawWaitMs",
    "removeWaitMs",
    "color",
    "padding",
    "animationSpeedMs",
    "lineWidthMin",
    "lineWidthMax",
    "opacity",
    "segments",
    "coverage",
    "scrollJs",
    "scrollWaitJs",
    "drawJs",
    "removeJs"
})
@Generated("jsonschema2pojo")
public class HighlightConfig {

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("scrollWaitMs")
    private Integer scrollWaitMs;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("drawWaitMs")
    private Integer drawWaitMs;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("removeWaitMs")
    private Integer removeWaitMs;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("color")
    private String color;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("padding")
    private Integer padding;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("animationSpeedMs")
    private Integer animationSpeedMs;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("lineWidthMin")
    private Integer lineWidthMin;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("lineWidthMax")
    private Integer lineWidthMax;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("opacity")
    private Double opacity;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("segments")
    private Integer segments;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("coverage")
    private Double coverage;
    /**
     * JS file path or inline code for scrolling element into view
     * (Required)
     * 
     */
    @JsonProperty("scrollJs")
    @JsonPropertyDescription("JS file path or inline code for scrolling element into view")
    private String scrollJs;
    /**
     * JS file path or inline code for waiting after scroll
     * (Required)
     * 
     */
    @JsonProperty("scrollWaitJs")
    @JsonPropertyDescription("JS file path or inline code for waiting after scroll")
    private String scrollWaitJs;
    /**
     * JS file path or inline code for drawing the highlight
     * (Required)
     * 
     */
    @JsonProperty("drawJs")
    @JsonPropertyDescription("JS file path or inline code for drawing the highlight")
    private String drawJs;
    /**
     * JS file path or inline code for removing the highlight
     * (Required)
     * 
     */
    @JsonProperty("removeJs")
    @JsonPropertyDescription("JS file path or inline code for removing the highlight")
    private String removeJs;

    /**
     * No args constructor for use in serialization
     * 
     */
    public HighlightConfig() {
    }

    /**
     * 
     * @param scrollJs
     *     JS file path or inline code for scrolling element into view.
     * @param removeJs
     *     JS file path or inline code for removing the highlight.
     * @param drawJs
     *     JS file path or inline code for drawing the highlight.
     * @param scrollWaitJs
     *     JS file path or inline code for waiting after scroll.
     */
    public HighlightConfig(Integer scrollWaitMs, Integer drawWaitMs, Integer removeWaitMs, String color, Integer padding, Integer animationSpeedMs, Integer lineWidthMin, Integer lineWidthMax, Double opacity, Integer segments, Double coverage, String scrollJs, String scrollWaitJs, String drawJs, String removeJs) {
        super();
        this.scrollWaitMs = scrollWaitMs;
        this.drawWaitMs = drawWaitMs;
        this.removeWaitMs = removeWaitMs;
        this.color = color;
        this.padding = padding;
        this.animationSpeedMs = animationSpeedMs;
        this.lineWidthMin = lineWidthMin;
        this.lineWidthMax = lineWidthMax;
        this.opacity = opacity;
        this.segments = segments;
        this.coverage = coverage;
        this.scrollJs = scrollJs;
        this.scrollWaitJs = scrollWaitJs;
        this.drawJs = drawJs;
        this.removeJs = removeJs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("scrollWaitMs")
    public Integer getScrollWaitMs() {
        return scrollWaitMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("scrollWaitMs")
    public void setScrollWaitMs(Integer scrollWaitMs) {
        this.scrollWaitMs = scrollWaitMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("drawWaitMs")
    public Integer getDrawWaitMs() {
        return drawWaitMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("drawWaitMs")
    public void setDrawWaitMs(Integer drawWaitMs) {
        this.drawWaitMs = drawWaitMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("removeWaitMs")
    public Integer getRemoveWaitMs() {
        return removeWaitMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("removeWaitMs")
    public void setRemoveWaitMs(Integer removeWaitMs) {
        this.removeWaitMs = removeWaitMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("color")
    public String getColor() {
        return color;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("color")
    public void setColor(String color) {
        this.color = color;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("padding")
    public Integer getPadding() {
        return padding;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("padding")
    public void setPadding(Integer padding) {
        this.padding = padding;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("animationSpeedMs")
    public Integer getAnimationSpeedMs() {
        return animationSpeedMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("animationSpeedMs")
    public void setAnimationSpeedMs(Integer animationSpeedMs) {
        this.animationSpeedMs = animationSpeedMs;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("lineWidthMin")
    public Integer getLineWidthMin() {
        return lineWidthMin;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("lineWidthMin")
    public void setLineWidthMin(Integer lineWidthMin) {
        this.lineWidthMin = lineWidthMin;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("lineWidthMax")
    public Integer getLineWidthMax() {
        return lineWidthMax;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("lineWidthMax")
    public void setLineWidthMax(Integer lineWidthMax) {
        this.lineWidthMax = lineWidthMax;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("opacity")
    public Double getOpacity() {
        return opacity;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("opacity")
    public void setOpacity(Double opacity) {
        this.opacity = opacity;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("segments")
    public Integer getSegments() {
        return segments;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("segments")
    public void setSegments(Integer segments) {
        this.segments = segments;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("coverage")
    public Double getCoverage() {
        return coverage;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("coverage")
    public void setCoverage(Double coverage) {
        this.coverage = coverage;
    }

    /**
     * JS file path or inline code for scrolling element into view
     * (Required)
     * 
     */
    @JsonProperty("scrollJs")
    public String getScrollJs() {
        return scrollJs;
    }

    /**
     * JS file path or inline code for scrolling element into view
     * (Required)
     * 
     */
    @JsonProperty("scrollJs")
    public void setScrollJs(String scrollJs) {
        this.scrollJs = scrollJs;
    }

    /**
     * JS file path or inline code for waiting after scroll
     * (Required)
     * 
     */
    @JsonProperty("scrollWaitJs")
    public String getScrollWaitJs() {
        return scrollWaitJs;
    }

    /**
     * JS file path or inline code for waiting after scroll
     * (Required)
     * 
     */
    @JsonProperty("scrollWaitJs")
    public void setScrollWaitJs(String scrollWaitJs) {
        this.scrollWaitJs = scrollWaitJs;
    }

    /**
     * JS file path or inline code for drawing the highlight
     * (Required)
     * 
     */
    @JsonProperty("drawJs")
    public String getDrawJs() {
        return drawJs;
    }

    /**
     * JS file path or inline code for drawing the highlight
     * (Required)
     * 
     */
    @JsonProperty("drawJs")
    public void setDrawJs(String drawJs) {
        this.drawJs = drawJs;
    }

    /**
     * JS file path or inline code for removing the highlight
     * (Required)
     * 
     */
    @JsonProperty("removeJs")
    public String getRemoveJs() {
        return removeJs;
    }

    /**
     * JS file path or inline code for removing the highlight
     * (Required)
     * 
     */
    @JsonProperty("removeJs")
    public void setRemoveJs(String removeJs) {
        this.removeJs = removeJs;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(HighlightConfig.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("scrollWaitMs");
        sb.append('=');
        sb.append(((this.scrollWaitMs == null)?"<null>":this.scrollWaitMs));
        sb.append(',');
        sb.append("drawWaitMs");
        sb.append('=');
        sb.append(((this.drawWaitMs == null)?"<null>":this.drawWaitMs));
        sb.append(',');
        sb.append("removeWaitMs");
        sb.append('=');
        sb.append(((this.removeWaitMs == null)?"<null>":this.removeWaitMs));
        sb.append(',');
        sb.append("color");
        sb.append('=');
        sb.append(((this.color == null)?"<null>":this.color));
        sb.append(',');
        sb.append("padding");
        sb.append('=');
        sb.append(((this.padding == null)?"<null>":this.padding));
        sb.append(',');
        sb.append("animationSpeedMs");
        sb.append('=');
        sb.append(((this.animationSpeedMs == null)?"<null>":this.animationSpeedMs));
        sb.append(',');
        sb.append("lineWidthMin");
        sb.append('=');
        sb.append(((this.lineWidthMin == null)?"<null>":this.lineWidthMin));
        sb.append(',');
        sb.append("lineWidthMax");
        sb.append('=');
        sb.append(((this.lineWidthMax == null)?"<null>":this.lineWidthMax));
        sb.append(',');
        sb.append("opacity");
        sb.append('=');
        sb.append(((this.opacity == null)?"<null>":this.opacity));
        sb.append(',');
        sb.append("segments");
        sb.append('=');
        sb.append(((this.segments == null)?"<null>":this.segments));
        sb.append(',');
        sb.append("coverage");
        sb.append('=');
        sb.append(((this.coverage == null)?"<null>":this.coverage));
        sb.append(',');
        sb.append("scrollJs");
        sb.append('=');
        sb.append(((this.scrollJs == null)?"<null>":this.scrollJs));
        sb.append(',');
        sb.append("scrollWaitJs");
        sb.append('=');
        sb.append(((this.scrollWaitJs == null)?"<null>":this.scrollWaitJs));
        sb.append(',');
        sb.append("drawJs");
        sb.append('=');
        sb.append(((this.drawJs == null)?"<null>":this.drawJs));
        sb.append(',');
        sb.append("removeJs");
        sb.append('=');
        sb.append(((this.removeJs == null)?"<null>":this.removeJs));
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
        result = ((result* 31)+((this.drawWaitMs == null)? 0 :this.drawWaitMs.hashCode()));
        result = ((result* 31)+((this.coverage == null)? 0 :this.coverage.hashCode()));
        result = ((result* 31)+((this.padding == null)? 0 :this.padding.hashCode()));
        result = ((result* 31)+((this.removeJs == null)? 0 :this.removeJs.hashCode()));
        result = ((result* 31)+((this.color == null)? 0 :this.color.hashCode()));
        result = ((result* 31)+((this.animationSpeedMs == null)? 0 :this.animationSpeedMs.hashCode()));
        result = ((result* 31)+((this.lineWidthMax == null)? 0 :this.lineWidthMax.hashCode()));
        result = ((result* 31)+((this.segments == null)? 0 :this.segments.hashCode()));
        result = ((result* 31)+((this.scrollJs == null)? 0 :this.scrollJs.hashCode()));
        result = ((result* 31)+((this.scrollWaitMs == null)? 0 :this.scrollWaitMs.hashCode()));
        result = ((result* 31)+((this.drawJs == null)? 0 :this.drawJs.hashCode()));
        result = ((result* 31)+((this.scrollWaitJs == null)? 0 :this.scrollWaitJs.hashCode()));
        result = ((result* 31)+((this.lineWidthMin == null)? 0 :this.lineWidthMin.hashCode()));
        result = ((result* 31)+((this.removeWaitMs == null)? 0 :this.removeWaitMs.hashCode()));
        result = ((result* 31)+((this.opacity == null)? 0 :this.opacity.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof HighlightConfig) == false) {
            return false;
        }
        HighlightConfig rhs = ((HighlightConfig) other);
        return ((((((((((((((((this.drawWaitMs == rhs.drawWaitMs)||((this.drawWaitMs!= null)&&this.drawWaitMs.equals(rhs.drawWaitMs)))&&((this.coverage == rhs.coverage)||((this.coverage!= null)&&this.coverage.equals(rhs.coverage))))&&((this.padding == rhs.padding)||((this.padding!= null)&&this.padding.equals(rhs.padding))))&&((this.removeJs == rhs.removeJs)||((this.removeJs!= null)&&this.removeJs.equals(rhs.removeJs))))&&((this.color == rhs.color)||((this.color!= null)&&this.color.equals(rhs.color))))&&((this.animationSpeedMs == rhs.animationSpeedMs)||((this.animationSpeedMs!= null)&&this.animationSpeedMs.equals(rhs.animationSpeedMs))))&&((this.lineWidthMax == rhs.lineWidthMax)||((this.lineWidthMax!= null)&&this.lineWidthMax.equals(rhs.lineWidthMax))))&&((this.segments == rhs.segments)||((this.segments!= null)&&this.segments.equals(rhs.segments))))&&((this.scrollJs == rhs.scrollJs)||((this.scrollJs!= null)&&this.scrollJs.equals(rhs.scrollJs))))&&((this.scrollWaitMs == rhs.scrollWaitMs)||((this.scrollWaitMs!= null)&&this.scrollWaitMs.equals(rhs.scrollWaitMs))))&&((this.drawJs == rhs.drawJs)||((this.drawJs!= null)&&this.drawJs.equals(rhs.drawJs))))&&((this.scrollWaitJs == rhs.scrollWaitJs)||((this.scrollWaitJs!= null)&&this.scrollWaitJs.equals(rhs.scrollWaitJs))))&&((this.lineWidthMin == rhs.lineWidthMin)||((this.lineWidthMin!= null)&&this.lineWidthMin.equals(rhs.lineWidthMin))))&&((this.removeWaitMs == rhs.removeWaitMs)||((this.removeWaitMs!= null)&&this.removeWaitMs.equals(rhs.removeWaitMs))))&&((this.opacity == rhs.opacity)||((this.opacity!= null)&&this.opacity.equals(rhs.opacity))));
    }

}
