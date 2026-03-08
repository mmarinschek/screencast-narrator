COMMON := api/common
PY_GEN := api/python-client/src/screencast_narrator_client/generated
TS_GEN := api/typescript-client/src/generated

.PHONY: generate generate-python generate-typescript generate-java test

generate: generate-python generate-typescript
	@echo "Done."

generate-python: $(PY_GEN)/storyboard_types.py $(PY_GEN)/qr_payload_types.py $(PY_GEN)/__init__.py

$(PY_GEN)/storyboard_types.py: $(COMMON)/storyboard-schema.json
	@mkdir -p $(PY_GEN)
	datamodel-codegen \
		--input $< \
		--output-model-type pydantic_v2.BaseModel \
		--use-standard-collections \
		--use-union-operator \
		--target-python-version 3.11 \
		--snake-case-field \
		--allow-population-by-field-name \
		--output $@

$(PY_GEN)/qr_payload_types.py: $(COMMON)/qr-payload-schema.json
	@mkdir -p $(PY_GEN)
	datamodel-codegen \
		--input $< \
		--output-model-type pydantic_v2.BaseModel \
		--use-standard-collections \
		--use-union-operator \
		--target-python-version 3.11 \
		--snake-case-field \
		--allow-population-by-field-name \
		--output $@

$(PY_GEN)/__init__.py: $(PY_GEN)/storyboard_types.py $(PY_GEN)/qr_payload_types.py
	@printf '%s\n' \
		'"""Generated types from JSON schemas — do not edit manually."""' \
		'' \
		'from screencast_narrator_client.generated.storyboard_types import (' \
		'    HighlightStyle,' \
		'    Model as StoryboardModel,' \
		'    Narration,' \
		'    Options,' \
		'    ScreenAction,' \
		'    ScreenActionTiming,' \
		'    ScreenActionType,' \
		')' \
		'from screencast_narrator_client.generated.qr_payload_types import (' \
		'    MarkerPosition,' \
		'    SyncType,' \
		')' \
		'' \
		'__all__ = [' \
		'    "HighlightStyle",' \
		'    "MarkerPosition",' \
		'    "Narration",' \
		'    "Options",' \
		'    "ScreenAction",' \
		'    "ScreenActionTiming",' \
		'    "ScreenActionType",' \
		'    "StoryboardModel",' \
		'    "SyncType",' \
		']' > $@

generate-typescript: $(TS_GEN)/storyboard-types.ts $(TS_GEN)/qr-payload-types.ts

$(TS_GEN)/storyboard-types.ts: $(COMMON)/storyboard-schema.json
	@mkdir -p $(TS_GEN)
	npx json-schema-to-typescript --unreachableDefinitions $< > $@

$(TS_GEN)/qr-payload-types.ts: $(COMMON)/qr-payload-schema.json
	@mkdir -p $(TS_GEN)
	npx json-schema-to-typescript --unreachableDefinitions $< > $@

generate-java:
	mvn generate-sources -f api/java-client/pom.xml

test:
	DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest
