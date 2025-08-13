import { extractTimeSlots, extractVolumeSlots, extractLanguage, extractRoomSlot, extractDeviceSlot } from "../src/router/slots.js";
import { ruleFirstRoute } from "../src/router/router.js";

function expect(cond: boolean, msg: string){ if(!cond) throw new Error(msg); }

// Time slots (≥10)
expect(extractTimeSlots("hoppa fram 30 sek").seconds === 30, "30 sek");
expect(extractTimeSlots("spola tillbaka en halv minut").seconds === 30, "en halv minut=30");
expect(extractTimeSlots("hoppa fram två minuter").seconds === 120, "två minuter=120");
expect(extractTimeSlots("hoppa tillbaka 90 s").seconds === 90, "90 s");
expect(extractTimeSlots("till 1:23").to === "1:23", "to 1:23");
expect(extractTimeSlots("vid 00:45").to === "00:45", "to 00:45");
expect(extractTimeSlots("gå till början").endpoint === "START", "endpoint START");
expect(extractTimeSlots("hoppa till slutet").endpoint === "END", "endpoint END");
expect(extractTimeSlots("hoppa till intro").endpoint === "INTRO", "endpoint INTRO");
expect(extractTimeSlots("hoppa till recap").endpoint === "RECAP", "endpoint RECAP");
expect(extractTimeSlots("hoppa till reklam").endpoint === "ADS", "endpoint ADS");

// Volume slots (≥6)
expect(extractVolumeSlots("sätt volymen till 50% ").level === 50, "set 50%");
expect(extractVolumeSlots("volym 30").level === 30, "level bare 30");
expect(extractVolumeSlots("höj 20%").delta === 20, "delta up 20");
expect(extractVolumeSlots("sänk 15%").delta === -15, "delta down 15");
expect(extractVolumeSlots("max volym").level === 100, "max=100");
expect(extractVolumeSlots("tyst").level === 0, "min=0");
expect(extractVolumeSlots("höj").delta === 10, "delta default up");
expect(extractVolumeSlots("sänk").delta === -10, "delta default down");

// Language
expect(extractLanguage("svenska") === "svenska", "svenska");

// Room/device (≥6)
expect(extractRoomSlot("spela i köket") === "köket", "room köket");
expect(extractRoomSlot("i vardagsrum") === "vardagsrummet", "room vardagsrummet alias");
expect(extractRoomSlot("till sovrummet") === "sovrummet", "room sovrummet");
expect(extractRoomSlot("på kontoret") === "kontoret", "room kontoret");
expect(extractDeviceSlot("spela på tv") === "tv", "device tv");
expect(extractDeviceSlot("spela på stereo") === "högtalare", "device alias stereo->högtalare");
expect(extractDeviceSlot("spela på kromecast") === "chromecast", "device alias kromecast->chromecast");
expect(extractDeviceSlot("spela på sound bar") === "soundbar", "device alias sound bar->soundbar");
expect(extractDeviceSlot("spotify klient") === "spotify", "device alias spotify klient->spotify");

// TRANSFER routing
const r1 = ruleFirstRoute("casta till tv");
expect(!!r1 && r1.name === "TRANSFER" && r1.args?.device === "tv", "transfer -> tv");
const r2 = ruleFirstRoute("spela på köket");
expect(!!r2 && r2.name === "TRANSFER" && r2.args?.device === "köket", "transfer -> köket");
const r3 = ruleFirstRoute("byt till stereo");
expect(!!r3 && r3.name === "TRANSFER" && r3.args?.device === "högtalare", "transfer -> högtalare");
const rNone = ruleFirstRoute("vad är klockan");
expect(rNone === null, "no route for unrelated query");

console.log("OK slots_and_router.test (extended)");


