import chess
from uci.adapter import UCIAdapter


def test_uci_command_returns_uciok():
    adapter = UCIAdapter()
    response = adapter.handle("uci")
    assert "uciok" in response
    assert "id name" in response
    assert "id author" in response


def test_isready_returns_readyok():
    adapter = UCIAdapter()
    assert adapter.handle("isready") == "readyok"


def test_unknown_command_returns_none():
    adapter = UCIAdapter()
    assert adapter.handle("nonsense") is None


def test_position_startpos_sets_starting_board():
    adapter = UCIAdapter()
    adapter.handle("position startpos")
    assert adapter.board.fen() == chess.Board().fen()


def test_position_startpos_with_moves():
    adapter = UCIAdapter()
    adapter.handle("position startpos moves e2e4 e7e5")
    expected = chess.Board()
    expected.push_uci("e2e4")
    expected.push_uci("e7e5")
    assert adapter.board.fen() == expected.fen()


def test_position_fen():
    adapter = UCIAdapter()
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    adapter.handle(f"position fen {fen}")
    # python-chess normalizes en passant square when no capture is possible
    assert adapter.board.fen() == chess.Board(fen).fen()


def test_go_returns_bestmove():
    adapter = UCIAdapter(depth=1)
    adapter.handle("position startpos")
    response = adapter.handle("go depth 1")
    assert response is not None
    assert response.startswith("bestmove ")
    move_uci = response.split()[1]
    board = chess.Board()
    assert chess.Move.from_uci(move_uci) in board.legal_moves


def test_ucinewgame_resets_board():
    adapter = UCIAdapter()
    adapter.handle("position startpos moves e2e4")
    adapter.handle("ucinewgame")
    assert adapter.board.fen() == chess.Board().fen()


def test_quit_returns_sentinel():
    adapter = UCIAdapter()
    assert adapter.handle("quit") == "__quit__"
