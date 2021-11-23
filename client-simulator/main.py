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
    pgn: Optional[TextIO]
    games: List[int]

app = typer.Typer()
app_options = AppOptions("", None, [])

def get_random_fen() -> str:
    """ Generates a random fen """
    game = random.choice(app_options.games)
    board = game.board()
    for move in game.mainline_moves():
        if random.choice([False, True]):
            break
        board.push(move)
    return game.board().fen()


def analyse_board(fen: str) -> Optional[str]:
    """ Send fen to service for analysis """
    result = requests.post(app_options.url, json={fen: fen})
    if not result.ok:
        return None
    return result.text


@app.command()
def throughput(timeout: int = typer.Argument(120, help="Time to run for in seconds")):
    """ Send sequental requests as quickly as possible """
    start_time = datetime.now()
    current_time = start_time

    while current_time - start_time <= timedelta(seconds=timeout):
        typer.echo(get_random_fen())
        current_time = datetime.now()

    typer.echo(f"time elappsed: {current_time - start_time}")


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
def main(url: str = typer.Option("localhost", help="URL of the ingress")):
    app_options.url = url

    with open("./lichess_db_standard_rated_2013-01.pgn") as pgn:
        offset = pgn.tell()
        game = chess.pgn.read_headers(pgn)
        while game is not None:
            app_options.games.append(offset)
            game = chess.pgn.read_headers(pgn)

    if len(app_options.games) == 0:
        typer.echo("Could not load games", err=True)
        typer.Exit()


if __name__ == "__main__":
    app()
