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
                override.getPadding() != null ? override.getPadding() : base.getPadding()
        );
    }

    public static SharedConfig.HighlightConfig applyTo(HighlightStyle style, SharedConfig.HighlightConfig config) {
        return new SharedConfig.HighlightConfig(
                config.scrollWaitMs(),
                style.getDrawDurationMs() != null ? style.getDrawDurationMs() : config.drawWaitMs(),
                config.removeWaitMs(),
                style.getColor() != null ? style.getColor() : config.color(),
                style.getPadding() != null ? style.getPadding() : config.padding(),
                style.getAnimationSpeedMs() != null ? style.getAnimationSpeedMs() : config.animationSpeedMs(),
                config.lineWidthMin(),
                config.lineWidthMax(),
                style.getOpacity() != null ? style.getOpacity() : config.opacity(),
                config.segments(),
                config.coverage(),
                config.scrollJs(),
                config.scrollWaitJs(),
                config.drawJs(),
                config.removeJs()
        );
    }
}
