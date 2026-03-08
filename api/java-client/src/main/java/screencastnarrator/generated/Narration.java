
package screencastnarrator.generated;

import java.util.ArrayList;
import java.util.List;
import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "narrationId",
    "text",
    "translations",
    "screenActions"
})
@Generated("jsonschema2pojo")
public class Narration {

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("narrationId")
    private Integer narrationId;
    @JsonProperty("text")
    private String text;
    /**
     * Translations keyed by language code
     * 
     */
    @JsonProperty("translations")
    @JsonPropertyDescription("Translations keyed by language code")
    private Translations translations;
    @JsonProperty("screenActions")
    private List<ScreenAction> screenActions = new ArrayList<ScreenAction>();

    /**
     * No args constructor for use in serialization
     * 
     */
    public Narration() {
    }

    /**
     * 
     * @param translations
     *     Translations keyed by language code.
     */
    public Narration(Integer narrationId, String text, Translations translations, List<ScreenAction> screenActions) {
        super();
        this.narrationId = narrationId;
        this.text = text;
        this.translations = translations;
        this.screenActions = screenActions;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("narrationId")
    public Integer getNarrationId() {
        return narrationId;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("narrationId")
    public void setNarrationId(Integer narrationId) {
        this.narrationId = narrationId;
    }

    @JsonProperty("text")
    public String getText() {
        return text;
    }

    @JsonProperty("text")
    public void setText(String text) {
        this.text = text;
    }

    /**
     * Translations keyed by language code
     * 
     */
    @JsonProperty("translations")
    public Translations getTranslations() {
        return translations;
    }

    /**
     * Translations keyed by language code
     * 
     */
    @JsonProperty("translations")
    public void setTranslations(Translations translations) {
        this.translations = translations;
    }

    @JsonProperty("screenActions")
    public List<ScreenAction> getScreenActions() {
        return screenActions;
    }

    @JsonProperty("screenActions")
    public void setScreenActions(List<ScreenAction> screenActions) {
        this.screenActions = screenActions;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(Narration.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("narrationId");
        sb.append('=');
        sb.append(((this.narrationId == null)?"<null>":this.narrationId));
        sb.append(',');
        sb.append("text");
        sb.append('=');
        sb.append(((this.text == null)?"<null>":this.text));
        sb.append(',');
        sb.append("translations");
        sb.append('=');
        sb.append(((this.translations == null)?"<null>":this.translations));
        sb.append(',');
        sb.append("screenActions");
        sb.append('=');
        sb.append(((this.screenActions == null)?"<null>":this.screenActions));
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
        result = ((result* 31)+((this.text == null)? 0 :this.text.hashCode()));
        result = ((result* 31)+((this.screenActions == null)? 0 :this.screenActions.hashCode()));
        result = ((result* 31)+((this.translations == null)? 0 :this.translations.hashCode()));
        result = ((result* 31)+((this.narrationId == null)? 0 :this.narrationId.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof Narration) == false) {
            return false;
        }
        Narration rhs = ((Narration) other);
        return (((((this.text == rhs.text)||((this.text!= null)&&this.text.equals(rhs.text)))&&((this.screenActions == rhs.screenActions)||((this.screenActions!= null)&&this.screenActions.equals(rhs.screenActions))))&&((this.translations == rhs.translations)||((this.translations!= null)&&this.translations.equals(rhs.translations))))&&((this.narrationId == rhs.narrationId)||((this.narrationId!= null)&&this.narrationId.equals(rhs.narrationId))));
    }

}
