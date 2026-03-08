
package screencastnarrator.generated;

import java.util.ArrayList;
import java.util.List;
import javax.annotation.processing.Generated;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * Schema for storyboard.json — the recording manifest written by clients.
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({
    "language",
    "narrations",
    "options"
})
@Generated("jsonschema2pojo")
public class StoryboardSchema {

    /**
     * Primary language code (e.g. 'en', 'de')
     * (Required)
     * 
     */
    @JsonProperty("language")
    @JsonPropertyDescription("Primary language code (e.g. 'en', 'de')")
    private String language;
    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("narrations")
    private List<Narration> narrations = new ArrayList<Narration>();
    @JsonProperty("options")
    private Options options;

    /**
     * No args constructor for use in serialization
     * 
     */
    public StoryboardSchema() {
    }

    /**
     * 
     * @param language
     *     Primary language code (e.g. 'en', 'de').
     */
    public StoryboardSchema(String language, List<Narration> narrations, Options options) {
        super();
        this.language = language;
        this.narrations = narrations;
        this.options = options;
    }

    /**
     * Primary language code (e.g. 'en', 'de')
     * (Required)
     * 
     */
    @JsonProperty("language")
    public String getLanguage() {
        return language;
    }

    /**
     * Primary language code (e.g. 'en', 'de')
     * (Required)
     * 
     */
    @JsonProperty("language")
    public void setLanguage(String language) {
        this.language = language;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("narrations")
    public List<Narration> getNarrations() {
        return narrations;
    }

    /**
     * 
     * (Required)
     * 
     */
    @JsonProperty("narrations")
    public void setNarrations(List<Narration> narrations) {
        this.narrations = narrations;
    }

    @JsonProperty("options")
    public Options getOptions() {
        return options;
    }

    @JsonProperty("options")
    public void setOptions(Options options) {
        this.options = options;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append(StoryboardSchema.class.getName()).append('@').append(Integer.toHexString(System.identityHashCode(this))).append('[');
        sb.append("language");
        sb.append('=');
        sb.append(((this.language == null)?"<null>":this.language));
        sb.append(',');
        sb.append("narrations");
        sb.append('=');
        sb.append(((this.narrations == null)?"<null>":this.narrations));
        sb.append(',');
        sb.append("options");
        sb.append('=');
        sb.append(((this.options == null)?"<null>":this.options));
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
        result = ((result* 31)+((this.options == null)? 0 :this.options.hashCode()));
        result = ((result* 31)+((this.language == null)? 0 :this.language.hashCode()));
        result = ((result* 31)+((this.narrations == null)? 0 :this.narrations.hashCode()));
        return result;
    }

    @Override
    public boolean equals(Object other) {
        if (other == this) {
            return true;
        }
        if ((other instanceof StoryboardSchema) == false) {
            return false;
        }
        StoryboardSchema rhs = ((StoryboardSchema) other);
        return ((((this.options == rhs.options)||((this.options!= null)&&this.options.equals(rhs.options)))&&((this.language == rhs.language)||((this.language!= null)&&this.language.equals(rhs.language))))&&((this.narrations == rhs.narrations)||((this.narrations!= null)&&this.narrations.equals(rhs.narrations))));
    }

}
