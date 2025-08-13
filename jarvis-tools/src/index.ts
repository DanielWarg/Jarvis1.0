import minimist from "minimist";
import { ruleFirstRoute } from "./router/router.js";

export function routeCommand(input: string) {
  return ruleFirstRoute(input) || { name: "NONE", args: {}, rationale: "No match" };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const argv = minimist(process.argv.slice(2));
  const tests = argv.test
    ? [
        "spela upp", "pausa", "stoppa",
        "hoppa fram 30 sek", "hoppa tillbaka en halv minut",
        "till 1:23", "gå till slutet"
      ]
    : [process.argv.slice(2).join(" ") || "hoppa fram 30 sek"];
  for (const t of tests) {
    const r = routeCommand(t);
    console.log(JSON.stringify({ input: t, result: r }));
  }
}


