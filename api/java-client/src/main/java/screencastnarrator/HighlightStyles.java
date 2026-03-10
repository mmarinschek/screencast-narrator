package screencastnarrator;

import screencastnarrator.generated.HighlightStyle;

public final class HighlightStyles {

    private HighlightStyles() {}

    public static HighlightStyle merge(HighlightStyle base, HighlightStyle override) {
        return new HighlightStyle(
                override.getColor() != null ? override.getColor() : base.getColor(),
                override.getAnimationSpeedMs() != null ? override.getAnimationSpeedMs() : base.getAnimationSpeedMs(),
                override.getDrawDurationMs() != null ? override.getDrawDurationMs() : base.getDrawDurationMs(),
                override.getOpacity() != null ? override.getOpacity() : base.getOpacity(),
                override.getPadding() != null ? override.getPadding() : base.getPadding(),
                override.getScrollWaitMs() != null ? override.getScrollWaitMs() : base.getScrollWaitMs(),
                override.getRemoveWaitMs() != null ? override.getRemoveWaitMs() : base.getRemoveWaitMs(),
                override.getLineWidthMin() != null ? override.getLineWidthMin() : base.getLineWidthMin(),
                override.getLineWidthMax() != null ? override.getLineWidthMax() : base.getLineWidthMax(),
                override.getSegments() != null ? override.getSegments() : base.getSegments(),
                override.getCoverage() != null ? override.getCoverage() : base.getCoverage()
        );
    }
}
