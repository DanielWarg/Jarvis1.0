#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from statistics import mean, median
import aiohttp
import pytest
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
from dotenv import load_dotenv

# Ladda miljövariabler från .env
load_dotenv()

# Konfigurera loggning med rich för färgad output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("router_test")

# Konfigurera paths
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Testdata för alla kommandon
TEST_CASES = {
    "PLAY": [
        "spela", "spela upp", "spela musik", "starta musik", "fortsätt spela",
        "kör musik", "kör igång musiken", "starta", "fortsätt", "play",
        "kör", "kör låten", "starta låten", "spela låten", "sätt igång",
        "börja spela", "spela vidare", "kör vidare"
    ],
    "PAUSE": [
        "pausa", "paus", "pausa musiken", "stoppa musiken", "pausa låten",
        "stoppa låten", "ta paus", "gör paus", "pause", "vänta",
        "pausa lite", "håll upp", "ta en paus", "paus i musiken",
        "pausar", "pausar musiken", "pausar låten"
    ],
    "STOP": [
        "stop", "stopp", "stoppa", "avsluta", "sluta spela",
        "avbryt", "stäng av musiken", "stäng av låten"
    ],
    "NEXT": [
        "nästa", "nästa låt", "hoppa över", "byt låt", "hoppa fram",
        "spela nästa", "nästa spår", "next", "skip", "skippa",
        "byt", "nästa sång", "framåt", "forward", "hoppa till nästa",
        "gå till nästa", "nästa track"
    ],
    "PREV": [
        "föregående", "förra", "förra låten", "spela förra", "föregående låt",
        "gå tillbaka", "previous", "förra spåret", "bakåt", "back",
        "förra sången", "tillbaka", "backa", "förra track",
        "spela föregående", "föregående spår"
    ],
    "SET_VOLUME": [
        ("sätt volymen till 50 procent", {"level": 50}),
        ("höj volymen till 80%", {"level": 80}),
        ("sänk volymen till 20%", {"level": 20}),
        ("volym 75", {"level": 75}),
        ("ställ volymen på 60", {"level": 60})
    ],
    "MUTE": [
        "mute", "stäng av ljudet", "tysta", "ljud av", "tyst läge",
        "dämpa", "tystna", "håll tyst", "inget ljud", "stäng ljudet",
        "tysta musiken", "tysta låten", "muta"
    ],
    "UNMUTE": [
        "unmute", "avmuta", "slå på ljud", "ljud på", "avdämpa",
        "sätt på ljudet", "aktivera ljud", "starta ljud", "återställ ljud",
        "ljud tillbaka", "sätt på ljudet igen"
    ],
    "REPEAT": [
        "repetera", "upprepa", "spela om", "spela igen", "repeat",
        "loop", "loopa", "om igen", "en gång till", "repetera låten",
        "upprepa låten", "spela om låten"
    ],
    "SHUFFLE": [
        "shuffle", "blanda", "slumpa", "spela blandat", "random",
        "slumpvis", "blanda låtar", "slumpmässigt", "shuffla",
        "blanda spellistan", "spela random"
    ],
    "LIKE": [
        "gilla", "like", "tumme upp", "favorit", "spara låt",
        "lägg till favoriter", "markera som favorit", "gilla låten",
        "spara denna låt", "lägg till i favoriter"
    ],
    "UNLIKE": [
        "ogilla", "unlike", "tumme ner", "ta bort favorit",
        "ta bort från favoriter", "avmarkera favorit", "ogilla låten",
        "ta bort denna låt", "sluta gilla"
    ]
}

# Förväntade källor för varje kommando
EXPECTED_SOURCES = {
    "PLAY": "router",
    "PAUSE": "router",
    "STOP": "router",
    "NEXT": "router",
    "PREV": "router",
    "SET_VOLUME": "router",
    "MUTE": "router",
    "UNMUTE": "router",
    "REPEAT": "router",
    "SHUFFLE": "router",
    "LIKE": "router",
    "UNLIKE": "router"
}

@dataclass
class TestResult:
    timestamp: str
    command: str
    phrase: str
    expected_intent: str
    actual_intent: Optional[str]
    expected_source: str
    actual_source: Optional[str]
    success: bool
    latency_ms: float
    error: Optional[str] = None

class RouterTester:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("API_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("API_KEY")
        self.results: List[TestResult] = []
        self.console = Console()
        self.results_file = os.path.join(
            RESULTS_DIR,
            f"router_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        
    def log_result(self, result: TestResult):
        """Logga ett testresultat till JSONL-filen"""
        with open(self.results_file, "a") as f:
            f.write(json.dumps(asdict(result)) + "\n")
        
    async def test_phrase(self, command: str, phrase: str, expected_args: Dict = None) -> TestResult:
        """Testa en specifik fras mot API:t"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            
            async with aiohttp.ClientSession() as session:
                # Först testa mot /agent/route för att se routerns beslut
                log.info(f"Testing phrase: '{phrase}' (Expected: {command})")
                
                start_time = datetime.now()
                async with session.post(
                    f"{self.base_url}/agent/route",
                    json={"text": phrase},
                    headers=headers
                ) as resp:
                    route_data = await resp.json()
                    log.debug(f"Route response: {json.dumps(route_data, indent=2)}")
                
                # Sedan testa mot /api/chat för att se slutresultatet
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={"prompt": phrase},
                    headers=headers
                ) as resp:
                    chat_data = await resp.json()
                    log.debug(f"Chat response: {json.dumps(chat_data, indent=2)}")
                
                end_time = datetime.now()
                latency = (end_time - start_time).total_seconds() * 1000
                
                # Validera resultatet
                success = True
                error = None
                actual_intent = None
                actual_source = None
                
                if "meta" in chat_data and "tool" in chat_data["meta"]:
                    tool_data = chat_data["meta"]["tool"]
                    actual_intent = tool_data.get("name")
                    actual_source = tool_data.get("source")
                    
                    # Validera intent
                    if actual_intent != command:
                        success = False
                        error = f"Intent mismatch: expected {command}, got {actual_intent}"
                    
                    # Validera source
                    expected_source = EXPECTED_SOURCES[command]
                    if actual_source != expected_source:
                        success = False
                        error = f"Source mismatch: expected {expected_source}, got {actual_source}"
                    
                    # Validera args om specificerade
                    if expected_args:
                        actual_args = tool_data.get("args", {})
                        if actual_args != expected_args:
                            success = False
                            error = f"Args mismatch: expected {expected_args}, got {actual_args}"
                else:
                    success = False
                    error = "No tool metadata in response"
                
                result = TestResult(
                    timestamp=datetime.now().isoformat(),
                    command=command,
                    phrase=phrase,
                    expected_intent=command,
                    actual_intent=actual_intent,
                    expected_source=EXPECTED_SOURCES[command],
                    actual_source=actual_source,
                    success=success,
                    latency_ms=latency,
                    error=error
                )
                
                # Logga resultatet
                self.log_result(result)
                
                if not success:
                    log.error(f"Test failed for '{phrase}': {error}")
                else:
                    log.info(f"Test passed for '{phrase}' ({latency:.1f}ms)")
                
                return result
                
        except Exception as e:
            log.exception(f"Error testing phrase '{phrase}'")
            result = TestResult(
                timestamp=datetime.now().isoformat(),
                command=command,
                phrase=phrase,
                expected_intent=command,
                actual_intent=None,
                expected_source=EXPECTED_SOURCES[command],
                actual_source=None,
                success=False,
                latency_ms=0,
                error=str(e)
            )
            self.log_result(result)
            return result

    def print_results(self):
        """Skriv ut testresultaten i en snygg tabell"""
        # Skapa resultatstabell
        table = Table(title="Router Test Results")
        table.add_column("Command", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Passed", style="green", justify="right")
        table.add_column("Failed", style="red", justify="right")
        table.add_column("Avg Latency", justify="right")
        table.add_column("Med Latency", justify="right")
        
        # Gruppera resultat per kommando
        command_results = {}
        for result in self.results:
            if result.command not in command_results:
                command_results[result.command] = []
            command_results[result.command].append(result)
        
        # Beräkna statistik per kommando
        total_tests = 0
        total_passed = 0
        all_latencies = []
        
        for command, results in sorted(command_results.items()):
            passed = sum(1 for r in results if r.success)
            failed = len(results) - passed
            latencies = [r.latency_ms for r in results if r.success]
            
            total_tests += len(results)
            total_passed += passed
            all_latencies.extend(latencies)
            
            table.add_row(
                command,
                str(len(results)),
                str(passed),
                str(failed),
                f"{mean(latencies):.1f}ms" if latencies else "N/A",
                f"{median(latencies):.1f}ms" if latencies else "N/A"
            )
        
        # Lägg till totalsumma
        table.add_row(
            "TOTAL",
            str(total_tests),
            str(total_passed),
            str(total_tests - total_passed),
            f"{mean(all_latencies):.1f}ms" if all_latencies else "N/A",
            f"{median(all_latencies):.1f}ms" if all_latencies else "N/A",
            style="bold"
        )
        
        # Skriv ut tabellen
        self.console.print("\n")
        self.console.print(table)
        self.console.print(f"\nPass rate: {(total_passed/total_tests)*100:.1f}%")
        self.console.print(f"Results saved to: {self.results_file}\n")
        
        # Skriv ut eventuella fel
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            self.console.print("\nFailed tests:", style="red bold")
            for result in failed_results:
                self.console.print(f"  • {result.phrase}")
                self.console.print(f"    {result.error}", style="red")

async def main():
    # Skapa testaren
    tester = RouterTester()
    
    # Testa alla fraser
    for command, phrases in TEST_CASES.items():
        if isinstance(phrases[0], tuple):
            # Hantera specialfall med args (t.ex. SET_VOLUME)
            for phrase, expected_args in phrases:
                result = await tester.test_phrase(command, phrase, expected_args)
                tester.results.append(result)
        else:
            # Vanliga fraser utan args
            for phrase in phrases:
                result = await tester.test_phrase(command, phrase)
                tester.results.append(result)
    
    # Skriv ut resultaten
    tester.print_results()

    # Returnera exit code baserat på testresultat
    failed_tests = sum(1 for r in tester.results if not r.success)
    return 1 if failed_tests > 0 else 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log.warning("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        log.exception("Unexpected error")
        sys.exit(1)