# Simple double-entry bookkeeping application using curses

from dataclasses import dataclass
from datetime import datetime
from typing import List
import csv
import curses
import curses.textpad


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

    def get_transactions_text(self) -> List[str]:
        lines = [f"{'Datum':<12} {'Beschreibung':<20} {'Soll':<5} {'Haben':<5} {'Betrag':>10}"]
        for t in self.transactions:
            lines.append(
                f"{t.date:<12} {t.description:<20} {t.debit:<5} {t.credit:<5} {t.amount:>10.2f}"
            )
        return lines

    def get_accounts_text(self) -> List[str]:
        lines = [f"{'Nr.':<5} {'Name'}"]
        for acc in self.accounts.values():
            lines.append(f"{acc.number:<5} {acc.name}")
        return lines


def main(stdscr):
    accounts = [Account(i, f"Konto {i}") for i in range(1, 26)]
    ledger = Ledger(accounts)

    def prompt_text(prompt: str) -> str:
        """Ask the user for text input using curses.textpad"""
        stdscr.clear()
        stdscr.addstr(0, 0, prompt)
        editwin = curses.newwin(1, 60, 2, 0)
        box = curses.textpad.Textbox(editwin)
        curses.curs_set(1)
        text = box.edit().strip()
        curses.curs_set(0)
        return text

    def show_lines(lines: List[str]):
        stdscr.clear()
        for idx, line in enumerate(lines):
            stdscr.addstr(idx, 0, line)
        stdscr.addstr(len(lines) + 1, 0, "Taste drücken, um fortzufahren...")
        stdscr.refresh()
        stdscr.getch()

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Haushaltsbuch")
        stdscr.addstr(2, 0, "1. Buchung erfassen")
        stdscr.addstr(3, 0, "2. Buchungen anzeigen")
        stdscr.addstr(4, 0, "3. Konten anzeigen")
        stdscr.addstr(5, 0, "4. CSV Export")
        stdscr.addstr(6, 0, "5. Beenden")
        stdscr.addstr(8, 0, "Auswahl: ")
        stdscr.refresh()
        ch = stdscr.getch()

        if ch == ord("1"):
            description = prompt_text("Beschreibung:")
            debit = int(prompt_text("Soll-Konto:"))
            credit = int(prompt_text("Haben-Konto:"))
            amount = float(prompt_text("Betrag:"))
            ledger.record_transaction(description, debit, credit, amount)
            stdscr.addstr(4, 0, "Buchung erfasst. Taste drücken...")
            stdscr.getch()
        elif ch == ord("2"):
            show_lines(ledger.get_transactions_text())
        elif ch == ord("3"):
            show_lines(ledger.get_accounts_text())
        elif ch == ord("4"):
            filename = prompt_text("Dateiname [buchungen.csv]:") or "buchungen.csv"
            ledger.export_csv(filename)
            stdscr.addstr(4, 0, f"CSV unter {filename} gespeichert. Taste drücken...")
            stdscr.getch()
        elif ch == ord("5"):
            break

if __name__ == "__main__":
    curses.wrapper(main)
