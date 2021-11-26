#!/usr/bin/env python3.9

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import random
import time
import logging
import requests
import chess.pgn
import typer

logging.basicConfig(filename="client-simulator.log", filemode="w")
log = logging.getLogger("Client")

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
    result = requests.post(app_options.url, json={"fen": fen})
    if not result.ok:
        return None
    return result.text


@app.command()
def throughput(timeout: int = typer.Option(120, help="Time to run for in seconds")):
    """ Send sequental requests as quickly as possible """
    start_time = datetime.now()
    current_time = start_time

    completed: int = 0

    while current_time - start_time <= timedelta(seconds=timeout):
        result = analyse_board(get_random_fen().strip())
        if result is not None:
            typer.echo(f"Got {result} from API")
            completed += 1
        else:
            typer.echo(f"Didn't get a valid response from API")
        current_time = datetime.now()

    achieved_rate = completed / (current_time - start_time).total_seconds()
    typer.echo(f"Completed {completed} requests in "
               f"{(current_time - start_time).total_seconds()} seconds\n"
               f"yielding {achieved_rate} boards/second")


@app.command()
def const_rate(rate: int = typer.Argument(..., help="Rate at which to submit chess boards board/second"),
               timeout: Optional[int] = typer.Option(None, help="Time to run stress test for")):
    """ Send random chess boards at a constant rate """
    start_time = datetime.now()
    current_time = start_time

    expected_ellapse = timedelta(seconds=1/rate)
    completed: int = 0

    while timeout is None or current_time - start_time <= timedelta(seconds=timeout):
        result = analyse_board(get_random_fen().strip())
        typer.echo(f"Got {result} from API")
        completed += 1

        new_time = datetime.now()
        ellapsed_time = new_time - current_time

        if ellapsed_time < expected_ellapse:
            time.sleep((expected_ellapse - ellapsed_time).total_seconds())
            current_time = datetime.now()
        elif ellapsed_time > expected_ellapse:
            log.warning("Cant keep up took %s when should of taken %s",
                        ellapsed_time, expected_ellapse)
            current_time = new_time
        else:
            current_time = new_time


    achieved_rate = completed / (current_time - start_time).total_seconds()
    typer.echo(f"Completed {completed} requests in "
               f"{(current_time - start_time).total_seconds()} seconds\n"
               f"yielding {achieved_rate} boards/second")



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
def main(url: str = typer.Option("https://localhost:3030", help="URL of the ingress"),
         fen_file: str = typer.Option("lichess_jan_2013.fens", help="File containing FENs")):
    app_options.url = url

    with open(fen_file) as file:
        app_options.fens = file.readlines()

    if len(app_options.fens) == 0:
        typer.echo("Could not load fens", err=True)
        typer.Exit()


if __name__ == "__main__":
    app()
