#!/usr/bin/env python3.9

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, TextIO
import random
import requests
import chess.pgn
import typer

@dataclass
class AppOptions:
    """ Represents the global options in the client """
    url: str
    fens: List[str]

app = typer.Typer()
app_options = AppOptions("", [])

def get_random_fen() -> str:
    """ Returns a random FEN from the --fen-file """
    return random.choice(app_options.fens)


def analyse_board(fen: str) -> Optional[str]:
    """ Send fen to service for analysis """
    result = requests.post(app_options.url, json={fen: fen})
    if not result.ok:
        return None
    return result.text


@app.command()
def throughput(timeout: int = typer.Option(120, help="Time to run for in seconds")):
    """ Send sequental requests as quickly as possible """
    start_time = datetime.now()
    current_time = start_time

    while current_time - start_time <= timedelta(seconds=timeout):
        analyse_board(get_random_fen().strip())
        current_time = datetime.now()

    typer.echo(f"Time elappsed: {current_time - start_time}")


@app.command()
def const_rate(rate: int = typer.Argument(..., help="Rate at which to submit chess boards"),
               time: Optional[int] = typer.Argument(None, help="Time to run stress test for")):
    typer.echo(f"hi {rate}")


@app.command()
def convert_pgn(pgn_file: str, output_file: str):
    with open(output_file, "w") as output:
        with open(pgn_file) as pgn:
            game = chess.pgn.read_game(pgn)
            while game is not None:
                board = game.board()
                for move in game.mainline_moves():
                    board.push(move)
                    output.write(board.fen() + "\n")
                output.flush()
                game = chess.pgn.read_game(pgn)



@app.callback()
def main(url: str = typer.Option("localhost", help="URL of the ingress"),
         fen_file: str = typer.Option("lichess_jan_2013.fens", help="File containing FENs")):
    app_options.url = url

    with open(fen_file) as file:
        app_options.fens = file.readlines()

    if len(app_options.fens) == 0:
        typer.echo("Could not load fens", err=True)
        typer.Exit()


if __name__ == "__main__":
    app()
