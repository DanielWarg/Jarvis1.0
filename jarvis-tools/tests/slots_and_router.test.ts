import { extractTimeSlots, extractVolumeSlots, extractLanguage, extractRoomSlot, extractDeviceSlot } from "../src/router/slots.js";
import { ruleFirstRoute } from "../src/router/router.js";

function expect(cond: boolean, msg: string){ if(!cond) throw new Error(msg); }

// Time slots
expect(extractTimeSlots("hoppa fram 30 sek").seconds === 30, "30 sek");
expect(extractTimeSlots("spola tillbaka en halv minut").seconds === 30, "en halv minut=30");
expect(extractTimeSlots("till 1:23").to === "1:23", "to 1:23");

// Volume slots
expect(extractVolumeSlots("sätt volymen till 50% ").level === 50, "set 50%");
expect(extractVolumeSlots("höj 20%").delta === 20, "delta up 20");
expect(extractVolumeSlots("sänk").delta === -10, "delta default down");

// Language
expect(extractLanguage("svenska") === "svenska", "svenska");

// Room/device
expect(extractRoomSlot("spela i köket") === "köket", "room köket");
expect(extractRoomSlot("på kontoret") === "kontoret", "room kontoret");
expect(extractDeviceSlot("spela på tv") === "tv", "device tv");

// TRANSFER routing
const r = ruleFirstRoute("casta till tv");
expect(!!r && r.name === "TRANSFER" && r.args?.device === "tv", "transfer -> tv");

console.log("OK slots_and_router.test");


