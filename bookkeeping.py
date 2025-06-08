# Simple double-entry bookkeeping application using rich

from dataclasses import dataclass
from datetime import datetime
from typing import List
import csv

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt
except ImportError:
    raise SystemExit("The 'rich' package is required to run this application.")

console = Console()

@dataclass
class Account:
    number: int
    name: str

@dataclass
class Transaction:
    date: str
    description: str
    debit: int
    credit: int
    amount: float

class Ledger:
    def __init__(self, accounts: List[Account]):
        self.accounts = {acc.number: acc for acc in accounts}
        self.transactions: List[Transaction] = []

    def record_transaction(self, description: str, debit: int, credit: int, amount: float, date: str = None):
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        if debit not in self.accounts or credit not in self.accounts:
            raise ValueError("Invalid account number")
        self.transactions.append(Transaction(date, description, debit, credit, amount))

    def export_csv(self, filename: str):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'description', 'debit', 'credit', 'amount'])
            for t in self.transactions:
                writer.writerow([t.date, t.description, t.debit, t.credit, f"{t.amount:.2f}"])

    def show_transactions(self):
        table = Table(title="Buchungen")
        table.add_column("Datum")
        table.add_column("Beschreibung")
        table.add_column("Soll")
        table.add_column("Haben")
        table.add_column("Betrag", justify="right")
        for t in self.transactions:
            table.add_row(t.date, t.description, str(t.debit), str(t.credit), f"{t.amount:.2f}")
        console.print(table)

    def show_accounts(self):
        table = Table(title="Konten")
        table.add_column("Nr.")
        table.add_column("Name")
        for acc in self.accounts.values():
            table.add_row(str(acc.number), acc.name)
        console.print(table)


def main():
    accounts = [Account(i, f"Konto {i}") for i in range(1, 26)]
    ledger = Ledger(accounts)

    while True:
        console.print("\n[bold]Haushaltsbuch[/bold]")
        console.print("1. Buchung erfassen")
        console.print("2. Buchungen anzeigen")
        console.print("3. Konten anzeigen")
        console.print("4. CSV Export")
        console.print("5. Beenden")
        choice = Prompt.ask("Auswahl", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            description = Prompt.ask("Beschreibung")
            debit = int(Prompt.ask("Soll-Konto"))
            credit = int(Prompt.ask("Haben-Konto"))
            amount = float(Prompt.ask("Betrag"))
            ledger.record_transaction(description, debit, credit, amount)
            console.print("Buchung erfasst.")
        elif choice == "2":
            ledger.show_transactions()
        elif choice == "3":
            ledger.show_accounts()
        elif choice == "4":
            filename = Prompt.ask("Dateiname", default="buchungen.csv")
            ledger.export_csv(filename)
            console.print(f"CSV wurde unter {filename} gespeichert.")
        elif choice == "5":
            break

if __name__ == "__main__":
    main()
