Java Workout Encoder Deployment
================================

This module encodes YAML workout definitions into Garmin FIT workout files using the Garmin FIT SDK and SnakeYAML.

Two supported installation paths (choose one):

1. Lightweight (no Maven) – script + Makefile (recommended for simple deployments)
2. Maven build – reproducible shaded executable JAR

--------------------------------------------------
1. Lightweight Script / Makefile Workflow
--------------------------------------------------

Requirements:
- Java 17+ (javac + java on PATH)
- curl

Steps:

    cd workout_builder
    make java-deps      # downloads fit.jar and snakeyaml jar into java/lib/
    make java-build     # compiles sources into java/build/
    make encode-yaml YAML=examples/your_workout.yml

Resulting FIT file(s) appear in examples/output/.

To encode all example workouts:

    make encode-all

To run the encoder manually after java-build:

    java -cp java/build:java/lib/fit.jar:java/lib/snakeyaml-2.2.jar com.neuraltag.workout.EncodeYamlWorkout examples/your_workout.yml

Cleaning build artifacts:

    make clean

Updating dependencies (force re-download):

    bash java/fetch_deps.sh --force

--------------------------------------------------
2. Maven Shaded JAR Workflow
--------------------------------------------------

Requirements:
- Java 17+
- Apache Maven (mvn)

Build:

    cd workout_builder/java
    mvn -DskipTests package

Executable fat JAR created at:

    workout_builder/java/target/workout-encoder-0.1.0-SNAPSHOT-shaded.jar

Run:

    java -jar target/workout-encoder-0.1.0-SNAPSHOT-shaded.jar ../examples/your_workout.yml

Notes:
- The shaded JAR bundles FIT + SnakeYAML so you do not need external jars at runtime.
- Version pins are controlled in pom.xml (fit.sdk.version, snakeyaml.version).

--------------------------------------------------
Version Management
--------------------------------------------------

Update dependency versions by editing either:
- pom.xml (for Maven builds)
- java/fetch_deps.sh (for script builds) – keep versions in sync for consistency.

--------------------------------------------------
CI / Automation Suggestions
--------------------------------------------------

Option A (script):
    make -C workout_builder java-deps java-build encode-all

Option B (Maven):
    mvn -q -DskipTests -f workout_builder/java/pom.xml package

Publish artifacts:
- Commit generated FIT workouts (optional) or upload shaded JAR as a release asset.

--------------------------------------------------
Troubleshooting
--------------------------------------------------

Class not found (FileEncoder, etc.): Ensure fit.jar is present in java/lib or that you used the shaded JAR.

Wrong Java version: Confirm `java -version` reports 17 or later.

Stale jars after version change: Run `bash java/fetch_deps.sh --force`.

--------------------------------------------------
Security Considerations
--------------------------------------------------

Always pin dependency versions. Avoid executing untrusted YAML—this tool uses SnakeYAML SafeConstructor with LoaderOptions for safety.

--------------------------------------------------
License
--------------------------------------------------

See repository LICENSE. Garmin FIT SDK license applies to the FIT library; review Garmin terms if redistributing.
