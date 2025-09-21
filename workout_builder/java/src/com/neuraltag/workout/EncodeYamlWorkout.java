package com.neuraltag.workout;

// Moved from com.garmin.fit.examples to project namespace for deployment use.
// Original content preserved.

import com.garmin.fit.*;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.LoaderOptions;
import org.yaml.snakeyaml.constructor.SafeConstructor;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class EncodeYamlWorkout {
    private enum HrOffsetMode {
        add_100, raw
    }

    public static void main(String[] args) {
        if (args.length != 1) {
            System.err.println("Usage: EncodeYamlWorkout <workout.yml>\n(Note: workout name is taken from metadata.name in the YAML)");
            return;
        }
        String yamlPath = args[0];
        try {
            Map<String, Object> root = loadYaml(yamlPath);
            WorkoutBuildContext ctx = new WorkoutBuildContext(root);
            List<WorkoutStepMesg> stepMesgs = buildSteps(ctx);
            writeFitFile(ctx, stepMesgs);
            System.out.println(
                    "Created FIT workout with " + stepMesgs.size() + " steps (including repeat controllers).");
        } catch (Exception e) {
            System.err.println("Failed: " + e.getMessage());
            e.printStackTrace();
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> loadYaml(String path) throws Exception {
        // SnakeYAML 2.x: SafeConstructor now requires LoaderOptions
        LoaderOptions loaderOptions = new LoaderOptions();
        Yaml yaml = new Yaml(new SafeConstructor(loaderOptions));
        try (InputStream in = new FileInputStream(path)) {
            Object loaded = yaml.load(in);
            if (!(loaded instanceof Map)) {
                throw new IllegalArgumentException("Root YAML must be a map");
            }
            return (Map<String, Object>) loaded;
        }
    }

    private static class WorkoutBuildContext {
        String name;
        String description;
        HrOffsetMode hrOffsetMode = HrOffsetMode.add_100;
        Intensity defaultIntensity = Intensity.ACTIVE;
        String repeatModeDefault = "controller";
        List<Object> stepsRaw;

        @SuppressWarnings("unchecked")
        WorkoutBuildContext(Map<String, Object> root) {
            Map<String, Object> metadata = (Map<String, Object>) root.get("metadata");
            if (metadata == null)
                throw new IllegalArgumentException("metadata section required");
            name = (String) metadata.getOrDefault("name", "Workout");
            description = (String) metadata.get("description");
            Map<String, Object> options = (Map<String, Object>) root.get("options");
            if (options != null) {
                Object off = options.get("hr_offset_mode");
                if (off != null)
                    hrOffsetMode = HrOffsetMode.valueOf(off.toString());
                Object di = options.get("default_intensity");
                if (di != null)
                    defaultIntensity = parseIntensity(di.toString());
                Object rm = options.get("repeat_mode_default");
                if (rm != null)
                    repeatModeDefault = rm.toString();
            }
            stepsRaw = (List<Object>) root.get("steps");
            if (stepsRaw == null || stepsRaw.isEmpty())
                throw new IllegalArgumentException("steps list required");
        }
    }

    @SuppressWarnings("unchecked")
    private static List<WorkoutStepMesg> buildSteps(WorkoutBuildContext ctx) {
        List<WorkoutStepMesg> out = new ArrayList<>();
        for (Object s : ctx.stepsRaw) {
            if (!(s instanceof Map))
                throw new IllegalArgumentException("Step must be a map: " + s);
            Map<String, Object> stepMap = (Map<String, Object>) s;
            String type = (String) stepMap.get("type");
            if (type == null)
                type = stepMap.containsKey("children") ? "group" : "simple";
            if ("group".equals(type)) {
                handleGroup(stepMap, ctx, out);
            } else if ("simple".equals(type)) {
                out.add(buildSimple(stepMap, ctx, out.size()));
            } else {
                throw new IllegalArgumentException("Unsupported step type: " + type);
            }
        }
        for (int i = 0; i < out.size(); i++)
            out.get(i).setMessageIndex(i);
        return out;
    }

    @SuppressWarnings("unchecked")
    private static void handleGroup(Map<String, Object> group, WorkoutBuildContext ctx, List<WorkoutStepMesg> out) {
        List<Object> children = (List<Object>) group.get("children");
        if (children == null || children.isEmpty())
            throw new IllegalArgumentException("group missing children");
        Integer repeat = asInt(group.get("repeat"));
        String mode = (String) group.getOrDefault("mode", ctx.repeatModeDefault);
        int startIndex = out.size();
        for (Object c : children) {
            if (!(c instanceof Map))
                throw new IllegalArgumentException("child must be map");
            out.add(buildSimple((Map<String, Object>) c, ctx, out.size()));
        }
        if (repeat != null && repeat > 1) {
            if ("controller".equals(mode)) {
                WorkoutStepMesg rep = new WorkoutStepMesg();
                rep.setMessageIndex(out.size());
                rep.setDurationType(WktStepDuration.REPEAT_UNTIL_STEPS_CMPLT);
                rep.setDurationValue((long) startIndex);
                rep.setTargetType(WktStepTarget.OPEN);
                // Previously (repeat - 1) produced an off-by-one on device; device expects total repeats
                rep.setTargetValue((long) repeat);
                rep.setCustomTargetValueLow(0L);
                rep.setCustomTargetValueHigh(0L);
                out.add(rep);
            } else {
                for (int i = 0; i < repeat - 1; i++) {
                    for (Object c : children)
                        out.add(buildSimple((Map<String, Object>) c, ctx, out.size()));
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    private static WorkoutStepMesg buildSimple(Map<String, Object> stepMap, WorkoutBuildContext ctx, int messageIndex) {
        WorkoutStepMesg step = new WorkoutStepMesg();
        step.setMessageIndex(messageIndex);
        String name = (String) stepMap.getOrDefault("name", "Step " + messageIndex);
        step.setWktStepName(trimToLen(name, 15));
        Intensity intensity = parseIntensity(
                (String) stepMap.getOrDefault("intensity", ctx.defaultIntensity.name().toLowerCase()));
        step.setIntensity(intensity);
        Map<String, Object> duration = (Map<String, Object>) stepMap.get("duration");
        if (duration == null)
            throw new IllegalArgumentException("simple step missing duration");
        applyDuration(duration, step);
        Map<String, Object> target = (Map<String, Object>) stepMap.get("target");
        applyTarget(target, step, ctx);
        return step;
    }

    private static void applyDuration(Map<String, Object> duration, WorkoutStepMesg step) {
        Boolean open = asBool(duration.get("open"));
        if (Boolean.TRUE.equals(open)) {
            step.setDurationType(WktStepDuration.OPEN);
            step.setDurationValue(0L);
            return;
        }
        Object valueObj = duration.get("value");
        if (valueObj == null)
            throw new IllegalArgumentException("duration value required unless open");
        double value = Double.parseDouble(valueObj.toString());
        String unit = (String) duration.get("unit");
        if (unit == null)
            throw new IllegalArgumentException("duration unit required");
        unit = unit.toLowerCase();
        if (isAny(unit, "s", "sec", "secs", "second", "seconds")) {
            long ms = (long) (value * 1000.0);
            step.setDurationType(WktStepDuration.TIME);
            step.setDurationValue(ms);
        } else if (isAny(unit, "m", "min", "mins", "minute", "minutes")) {
            long ms = (long) (value * 60_000L);
            step.setDurationType(WktStepDuration.TIME);
            step.setDurationValue(ms);
        } else if ("km".equals(unit)) {
            long cm = (long) (value * 1000.0 * 100.0);
            step.setDurationType(WktStepDuration.DISTANCE);
            step.setDurationValue(cm);
        } else if ("m".equals(unit)) {
            long cm = (long) (value * 100.0);
            step.setDurationType(WktStepDuration.DISTANCE);
            step.setDurationValue(cm);
        } else {
            throw new IllegalArgumentException("Unsupported duration unit: " + unit);
        }
    }

    private static void applyTarget(Map<String, Object> target, WorkoutStepMesg step, WorkoutBuildContext ctx) {
        if (target == null) {
            step.setTargetType(WktStepTarget.OPEN);
            step.setTargetValue(0L);
            step.setCustomTargetValueLow(0L);
            step.setCustomTargetValueHigh(0L);
            return;
        }
        String type = (String) target.get("type");
        if (type == null)
            throw new IllegalArgumentException("target missing type");
        switch (type) {
            case "open":
                step.setTargetType(WktStepTarget.OPEN);
                step.setTargetValue(0L);
                step.setCustomTargetValueLow(0L);
                step.setCustomTargetValueHigh(0L);
                break;
            case "pace": {
                String val = target.get("value").toString();
                int speed = paceToSpeed(val);
                step.setTargetType(WktStepTarget.SPEED);
                step.setTargetValue(0L);
                step.setCustomTargetValueLow((long) speed);
                step.setCustomTargetValueHigh((long) speed);
                break;
            }
            case "pace_range": {
                String low = target.get("low").toString();
                String high = target.get("high").toString();
                int s1 = paceToSpeed(low);
                int s2 = paceToSpeed(high);
                long lo = Math.min(s1, s2);
                long hi = Math.max(s1, s2);
                step.setTargetType(WktStepTarget.SPEED);
                step.setTargetValue(0L);
                step.setCustomTargetValueLow(lo);
                step.setCustomTargetValueHigh(hi);
                break;
            }
            case "heart_rate_zone": {
                int zone = asIntRequired(target.get("zone"));
                step.setTargetType(WktStepTarget.HEART_RATE);
                step.setTargetValue((long) zone);
                zeroCustom(step);
                break;
            }
            case "heart_rate_range": {
                int low = asIntRequired(target.get("low"));
                int high = asIntRequired(target.get("high"));
                if (high <= low)
                    throw new IllegalArgumentException("heart_rate_range high must be > low");
                if (ctx.hrOffsetMode == HrOffsetMode.add_100) {
                    low += 100;
                    high += 100;
                }
                step.setTargetType(WktStepTarget.HEART_RATE);
                step.setTargetValue(0L);
                step.setCustomTargetValueLow((long) low);
                step.setCustomTargetValueHigh((long) high);
                break;
            }
            case "power_zone": {
                int zone = asIntRequired(target.get("zone"));
                step.setTargetType(WktStepTarget.POWER);
                step.setTargetValue((long) zone);
                zeroCustom(step);
                break;
            }
            case "power_range": {
                int low = asIntRequired(target.get("low"));
                int high = asIntRequired(target.get("high"));
                if (high <= low)
                    throw new IllegalArgumentException("power_range high must be > low");
                step.setTargetType(WktStepTarget.POWER);
                step.setTargetValue(0L);
                step.setCustomTargetValueLow((long) low);
                step.setCustomTargetValueHigh((long) high);
                break;
            }
            case "cadence_range": {
                int low = asIntRequired(target.get("low"));
                int high = asIntRequired(target.get("high"));
                if (high <= low)
                    throw new IllegalArgumentException("cadence_range high must be > low");
                step.setTargetType(WktStepTarget.CADENCE);
                step.setTargetValue(0L);
                step.setCustomTargetValueLow((long) low);
                step.setCustomTargetValueHigh((long) high);
                break;
            }
            default:
                throw new IllegalArgumentException("Unsupported target type: " + type);
        }
    }

    private static void writeFitFile(WorkoutBuildContext ctx, List<WorkoutStepMesg> steps) {
        WorkoutMesg workout = new WorkoutMesg();
        // Use YAML metadata name; sanitize & trim to typical Garmin limits
        String baseName = ctx.name;
        if (baseName == null || baseName.isBlank())
            baseName = "Workout";
        String wktName = trimToLen(sanitizeName(baseName), 30); // device friendly length
        workout.setWktName(wktName);
        workout.setSport(Sport.RUNNING);
        workout.setSubSport(SubSport.INVALID);
        workout.setNumValidSteps(steps.size());

        // Handle description (both short field and extended via memo_glob if needed)
        List<MemoGlobMesg> memoGlobs = new ArrayList<>();
        if (ctx.description != null && !ctx.description.isBlank()) {
            byte[] full = ctx.description.getBytes(StandardCharsets.UTF_8);
            // WorkoutMesg generated field length for wkt_description is 161 bytes (from SDK definition)
            int MAX_DESC_FIELD_BYTES = 161; // safety: matches generated profile length
            byte[] preview;
            if (full.length <= MAX_DESC_FIELD_BYTES) {
                preview = full;
            } else {
                // Reserve 3 bytes for ellipsis '...'
                int cut = MAX_DESC_FIELD_BYTES - 3;
                if (cut < 0) cut = 0; // safety
                preview = Arrays.copyOf(full, cut);
                // Avoid splitting multibyte UTF-8: backtrack to valid boundary
                cut = backtrackToUtf8Boundary(preview, cut);
                preview = Arrays.copyOf(preview, cut);
                // Append ellipsis
                preview = concat(preview, "...".getBytes(StandardCharsets.UTF_8));
            }
            workout.setWktDescription(new String(preview, StandardCharsets.UTF_8));
            // Always emit full description via memo_glob (even if short) for richer devices
            memoGlobs = buildMemoGlobsForDescription(full, WorkoutMesg.WktDescriptionFieldNum, MesgNum.WORKOUT, 0);
        }

        FileIdMesg fileId = new FileIdMesg();
        fileId.setType(File.WORKOUT);
        // Use GARMIN manufacturer so device will ingest; set a stable product id if
        // available.
        fileId.setManufacturer(Manufacturer.GARMIN);
        try {
            // If FileIdMesg exposes setGarminProduct (newer SDKs) use it; otherwise fall
            // back to setProduct.
            FileIdMesg.class.getMethod("setGarminProduct", Integer.class).invoke(fileId, 65534); // typical generic code
        } catch (Exception noMethod) {
            fileId.setProduct(65534); // fallback
        }
        fileId.setSerialNumber((long) (System.currentTimeMillis() & 0xFFFFFFFFL));
        fileId.setTimeCreated(new DateTime(new Date()));

        String filename = wktName.replace(' ', '_') + ".fit";
        try {
            FileEncoder encoder = new FileEncoder(new java.io.File(filename), Fit.ProtocolVersion.V1_0);
            encoder.write(fileId);
            encoder.write(workout);
            // Write memo_glob messages (extended description) before steps
            for (MemoGlobMesg mg : memoGlobs) {
                encoder.write(mg);
            }
            for (WorkoutStepMesg s : steps) {
                encoder.write(s);
            }
            encoder.close();
            System.out.println("Wrote " + filename);
        } catch (Exception e) {
            throw new RuntimeException("Failed writing FIT: " + e.getMessage(), e);
        }
    }

    private static List<MemoGlobMesg> buildMemoGlobsForDescription(byte[] utf8, int fieldNum, int mesgNum, int parentIndex) {
        List<MemoGlobMesg> out = new ArrayList<>();
        // FIT memo_glob data field capacity in generated profile: 250 bytes per message
        final int CHUNK = 250;
        int part = 0;
        for (int pos = 0; pos < utf8.length; ) {
            int remaining = utf8.length - pos;
            int take = Math.min(CHUNK, remaining);
            // Avoid splitting multi-byte UTF-8 characters across chunk boundary
            take = adjustChunkForUtf8(utf8, pos, take);
            MemoGlobMesg mg = new MemoGlobMesg();
            mg.setPartIndex((long) part);
            mg.setMesgNum(mesgNum);
            mg.setParentIndex(parentIndex); // workout message_index is 0 by construction
            mg.setFieldNum((short) fieldNum);
            for (int i = 0; i < take; i++) {
                short b = (short) (utf8[pos + i] & 0xFF);
                mg.setData(i, b);
            }
            out.add(mg);
            pos += take;
            part++;
        }
        return out;
    }

    private static int adjustChunkForUtf8(byte[] bytes, int offset, int proposed) {
        int end = offset + proposed;
        if (end >= bytes.length) return proposed; // last chunk fine
        // If bytes[end] is a continuation byte (10xxxxxx), backtrack until start of the character
        while (end > offset) {
            byte b = bytes[end - 1];
            if ((b & 0x80) == 0) { // single-byte ASCII
                break;
            }
            // If leading bits are 11xxxxxx we found the start of a multi-byte char
            if ((b & 0xC0) == 0xC0) {
                // Count expected length
                int expected = 0;
                if ((b & 0xE0) == 0xC0) expected = 2; // 110xxxxx
                else if ((b & 0xF0) == 0xE0) expected = 3; // 1110xxxx
                else if ((b & 0xF8) == 0xF0) expected = 4; // 11110xxx
                else expected = 1; // fallback
                int actual = 1;
                for (int i = end; i < bytes.length && (bytes[i] & 0xC0) == 0x80 && actual < expected; i++) actual++;
                if (actual != expected) {
                    // Incomplete sequence at boundary; move boundary earlier
                    end--;
                    continue;
                }
                break; // complete multi-byte char ends exactly at boundary
            }
            // continuation byte; move boundary earlier
            end--;
        }
        return end - offset;
    }

    private static int backtrackToUtf8Boundary(byte[] bytes, int len) {
        if (len >= bytes.length) return len;
        int i = len;
        // Move backwards while on continuation bytes (10xxxxxx)
        while (i > 0 && (bytes[i - 1] & 0xC0) == 0x80) {
            i--;
        }
        if (i == 0) return len; // give up; shouldn't happen for valid UTF-8
        return i;
    }

    private static byte[] concat(byte[] a, byte[] b) {
        byte[] out = new byte[a.length + b.length];
        System.arraycopy(a, 0, out, 0, a.length);
        System.arraycopy(b, 0, out, a.length, b.length);
        return out;
    }

    private static void zeroCustom(WorkoutStepMesg step) {
        step.setCustomTargetValueLow(0L);
        step.setCustomTargetValueHigh(0L);
    }

    private static boolean isAny(String val, String... opts) {
        for (String o : opts)
            if (val.equals(o))
                return true;
        return false;
    }

    private static String trimToLen(String s, int max) {
        return (s.length() <= max) ? s : s.substring(0, max);
    }

    private static String sanitizeName(String n) {
        return n.replaceAll("[^A-Za-z0-9 _-]", "");
    }

    private static Intensity parseIntensity(String raw) {
        if (raw == null)
            return Intensity.ACTIVE;
        switch (raw.toLowerCase()) {
            case "warmup":
                return Intensity.WARMUP;
            case "active":
                return Intensity.ACTIVE;
            case "rest":
                return Intensity.REST;
            case "cooldown":
                return Intensity.COOLDOWN;
            default:
                return Intensity.ACTIVE;
        }
    }

    private static int paceToSpeed(String pace) {
        pace = pace.trim();
        if (pace.matches("\\d+")) {
            int sec = Integer.parseInt(pace);
            return (int) Math.round((1000.0 / sec) * 1000.0);
        }
        String[] parts = pace.split(":");
        if (parts.length != 2)
            throw new IllegalArgumentException("Bad pace format (mm:ss): " + pace);
        int mm = Integer.parseInt(parts[0]);
        int ss = Integer.parseInt(parts[1]);
        int total = mm * 60 + ss;
        double mps = 1000.0 / total;
        return (int) Math.round(mps * 1000.0);
    }

    private static Integer asInt(Object o) {
        return (o == null) ? null : Integer.parseInt(o.toString());
    }

    private static int asIntRequired(Object o) {
        if (o == null)
            throw new IllegalArgumentException("integer field required");
        return Integer.parseInt(o.toString());
    }

    private static Boolean asBool(Object o) {
        return (o == null) ? null : Boolean.parseBoolean(o.toString());
    }
}
