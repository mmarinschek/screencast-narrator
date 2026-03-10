
package screencastnarrator.generated;

import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "highlightStyle",
    "voices",
    "debugOverlay",
    "fontSize"
})
@Generated("jsonschema2pojo")
public class Options {

    /**
     * User-customizable highlight appearance. All fields are optional — unset fields inherit from the shared config defaults.
     * 
     */
    @JsonProperty("highlightStyle")
    @JsonPropertyDescription("User-customizable highlight appearance. All fields are optional \u2014 unset fields inherit from the shared config defaults.")
    private HighlightStyle highlightStyle;
    /**
     * Named voice identities mapping alias to language-specific TTS voices (e.g. {"nathaly": {"en": "bf_alice", "de": "de_natasha"}})
     * 
     */
    @JsonProperty("voices")
    @JsonPropertyDescription("Named voice identities mapping alias to language-specific TTS voices (e.g. {\"nathaly\": {\"en\": \"bf_alice\", \"de\": \"de_natasha\"}})")
    private Voices voices;
    /**
     * Show debug overlay in the final video
     * 
     */
    @JsonProperty("debugOverlay")
    @JsonPropertyDescription("Show debug overlay in the final video")
    private Boolean debugOverlay;
    /**
     * Font size for debug overlay text
     * 
     */
    @JsonProperty("fontSize")
    @JsonPropertyDescription("Font size for debug overlay text")
    private Integer fontSize;

    /**
     * No args constructor for use in serialization
     * 
     */
    public Options() {
    }

    /**
     * 
     * @param debugOverlay
     *     Show debug overlay in the final video.
     * @param voices
     *     Named voice identities mapping alias to language-specific TTS voices (e.g. {"nathaly": {"en": "bf_alice", "de": "de_natasha"}}).
     * @param fontSize
     *     Font size for debug overlay text.
     */
    public Options(HighlightStyle highlightStyle, Voices voices, Boolean debugOverlay, Integer fontSize) {
        super();
        this.highlightStyle = highlightStyle;
        this.voices = voices;
        this.debugOverlay = debugOverlay;
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

    /**
     * Named voice identities mapping alias to language-specific TTS voices (e.g. {"nathaly": {"en": "bf_alice", "de": "de_natasha"}})
     * 
     */
    @JsonProperty("voices")
    public Voices getVoices() {
        return voices;
    }

    /**
     * Named voice identities mapping alias to language-specific TTS voices (e.g. {"nathaly": {"en": "bf_alice", "de": "de_natasha"}})
     * 
     */
    @JsonProperty("voices")
    public void setVoices(Voices voices) {
        this.voices = voices;
    }

    /**
     * Show debug overlay in the final video
     * 
     */
    @JsonProperty("debugOverlay")
    public Boolean getDebugOverlay() {
        return debugOverlay;
    }

    /**
     * Show debug overlay in the final video
     * 
     */
    @JsonProperty("debugOverlay")
    public void setDebugOverlay(Boolean debugOverlay) {
        this.debugOverlay = debugOverlay;
    }

    /**
     * Font size for debug overlay text
     * 
     */
    @JsonProperty("fontSize")
    public Integer getFontSize() {
        return fontSize;
    }

    /**
     * Font size for debug overlay text
     * 
     */
    @JsonProperty("fontSize")
    public void setFontSize(Integer fontSize) {
        this.fontSize = fontSize;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(Options.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("highlightStyle");
        sb.append('=');
        sb.append(((this.highlightStyle == null)?"<null>":this.highlightStyle));
        sb.append(',');
        sb.append("voices");
        sb.append('=');
        sb.append(((this.voices == null)?"<null>":this.voices));
        sb.append(',');
        sb.append("debugOverlay");
        sb.append('=');
        sb.append(((this.debugOverlay == null)?"<null>":this.debugOverlay));
        sb.append(',');
        sb.append("fontSize");
        sb.append('=');
        sb.append(((this.fontSize == null)?"<null>":this.fontSize));
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
        result = ((result* 31)+((this.voices == null)? 0 :this.voices.hashCode()));
        result = ((result* 31)+((this.fontSize == null)? 0 :this.fontSize.hashCode()));
        result = ((result* 31)+((this.debugOverlay == null)? 0 :this.debugOverlay.hashCode()));
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
        return (((((this.voices == rhs.voices)||((this.voices!= null)&&this.voices.equals(rhs.voices)))&&((this.fontSize == rhs.fontSize)||((this.fontSize!= null)&&this.fontSize.equals(rhs.fontSize))))&&((this.debugOverlay == rhs.debugOverlay)||((this.debugOverlay!= null)&&this.debugOverlay.equals(rhs.debugOverlay))))&&((this.highlightStyle == rhs.highlightStyle)||((this.highlightStyle!= null)&&this.highlightStyle.equals(rhs.highlightStyle))));
    }

}
