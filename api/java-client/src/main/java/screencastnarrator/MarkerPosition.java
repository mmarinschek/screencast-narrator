package screencastnarrator;

public enum MarkerPosition {
    START("start"),
    END("end");

    private final String value;

    MarkerPosition(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    @Override
    public String toString() {
        return value;
    }
}
