### Workout Builder Makefile
# Provides convenient targets to compile the Java FIT encoder and run it against example YAML workouts.

# ---- Configuration ----
JAVA_DIR      := java
JAVA_SRC_DIR  := $(JAVA_DIR)/src
JAVA_BUILD    := $(JAVA_DIR)/build
JAVA_LIB_DIR  := $(JAVA_DIR)/lib
FIT_JAR       := $(JAVA_LIB_DIR)/fit.jar
SNAKEYAML_JAR := $(JAVA_LIB_DIR)/snakeyaml-2.2.jar
CLASSPATH     := $(JAVA_BUILD):$(FIT_JAR):$(SNAKEYAML_JAR)

EXAMPLES_DIR  := examples
OUT_DIR       := $(EXAMPLES_DIR)/output

ENCODER_CLASS := com.neuraltag.workout.EncodeYamlWorkout

# Python (optional future) – currently only main model file present
PY_MODEL      := py/workout_definition.py
PYTHON        ?= python

.PHONY: help java-build clean encode-yaml encode-all list-examples ensure-out

help:
	@echo "Workout Builder Targets:";
	@echo "  make java-build            Compile Java encoder (EncodeYamlWorkout)";
	@echo "  make encode-yaml YAML=... [NAME=CustomName]  Generate FIT from YAML";
	@echo "  make encode-all            Run encoder for every YAML in $(EXAMPLES_DIR)";
	@echo "  make list-examples         List available example YAML files";
	@echo "  make clean                 Remove compiled classes";
	@echo "Variables:";
	@echo "  YAML=path/to/file.yml (required for encode-yaml)";
	@echo "  NAME=OverrideWorkoutName (optional)";

$(JAVA_BUILD):
	mkdir -p $(JAVA_BUILD)

java-build: $(JAVA_BUILD)
	@echo "Compiling Java sources..."
	@find $(JAVA_SRC_DIR) -name "*.java" > $(JAVA_BUILD)/sources.list
	@javac -cp $(FIT_JAR):$(SNAKEYAML_JAR):$(JAVA_SRC_DIR) @$(JAVA_BUILD)/sources.list -d $(JAVA_BUILD)
	@echo "Compilation complete."

clean:
	rm -rf $(JAVA_BUILD)

ensure-out:
	mkdir -p $(OUT_DIR)

encode-yaml: java-build ensure-out
	@if [ -z "$(YAML)" ]; then echo "ERROR: Provide YAML=path/to/workout.yml"; exit 1; fi
	@echo "Encoding $(YAML)..."
	@java -cp $(CLASSPATH) $(ENCODER_CLASS) $(YAML) $(NAME)
	@mv -f *.fit $(OUT_DIR) 2>/dev/null || true
	@echo "FIT file(s) moved to $(OUT_DIR)"

encode-all: java-build ensure-out
	@set -e; cnt=0; \
	for f in $(EXAMPLES_DIR)/*.yml $(EXAMPLES_DIR)/*.yaml; do \
	  [ -e "$$f" ] || continue; \
	  echo "---> Encoding $$f"; \
	  java -cp $(CLASSPATH) $(ENCODER_CLASS) $$f; \
	  cnt=$$((cnt+1)); \
	done; \
	mv -f *.fit $(OUT_DIR) 2>/dev/null || true; \
	echo "Encoded $$cnt workout(s). FIT files in $(OUT_DIR)";

list-examples:
	@ls -1 $(EXAMPLES_DIR)/*.yml $(EXAMPLES_DIR)/*.yaml 2>/dev/null || echo "No example YAML files found."

# Placeholder for future Python validation integration
.PHONY: validate-yaml
validate-yaml:
	@if [ -z "$(YAML)" ]; then echo "ERROR: Provide YAML=..."; exit 1; fi
	@echo "(Placeholder) Validate $(YAML) with Python model: $(PY_MODEL)"
	@$(PYTHON) $(PY_MODEL) $(YAML) || true

