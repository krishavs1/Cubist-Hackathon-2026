import chess
from engine.engine import Engine

def test_uci_handshake():
    engine = Engine()
    response = engine.handle_command("uci")
    assert "id name" in response
    assert "id author" in response
    assert "uciok" in response

def test_isready():
    engine = Engine()
    response = engine.handle_command("isready")
    assert response == "readyok"

def test_position_startpos():
    engine = Engine()
    engine.handle_command("position startpos")
    assert engine.board.fen() == chess.Board().fen()

def test_position_moves():
    engine = Engine()
    engine.handle_command("position startpos moves e2e4 e7e5")
    assert engine.board.fen() == chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2").fen()
