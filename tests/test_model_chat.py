# Standard
import os
import tempfile
from unittest.mock import MagicMock
import contextlib
import re
import openai

# Third Party
from rich.console import Console
import pytest

from instructlab.defaults import DEFAULTS
# First Party
from instructlab.model.chat import ConsoleChatBot
from instructlab.rag.document_store import DocumentStoreRetriever
from instructlab.rag.document_store_factory import create_document_retriever


@pytest.mark.parametrize(
    "model_path,expected_name",
    [
        ("/var/model/file", "file"),
        ("/var/model/directory/", "directory"),
        ("/var/model/directory/////", "directory"),
    ],
)
def test_model_name(model_path, expected_name):
    chatbot = ConsoleChatBot(model=model_path, client=None, loaded={})
    assert chatbot.model_name == expected_name


def test_retriever():
    with tempfile.TemporaryDirectory() as temp_dir:
        retriever: DocumentStoreRetriever = create_document_retriever(
            document_store_uri=os.path.join(temp_dir, "any.db"),
            document_store_collection_name="any",
            top_k=10,
            embedding_model_path=os.path.join(temp_dir, "embeddings.model"),
        )

        chatbot = ConsoleChatBot(model="any.model", client=None, retriever=retriever, loaded={})
        assert chatbot.retriever == retriever

        # verify there was an attempt to load an embeddings model
        # which should only happen if a document retriever is attempted to be used
        with contextlib.suppress(KeyboardInterrupt):
            try:
                chatbot.start_prompt(content="test", logger=None)
            except ValueError as e:
                assert DEFAULTS.GRANITE_EMBEDDINGS_MODEL_NAME in repr(e)



def handle_output(output):
    return re.sub(r"\s+", " ", output).strip()


def test_list_contexts_output():
    chatbot = ConsoleChatBot(model="/var/model/file", client=None, loaded={})

    def mock_sys_print(output):
        mock_sys_print.output = output

    chatbot._sys_print = mock_sys_print

    mock_prompt_session = MagicMock()
    mock_prompt_session.prompt.return_value = "/lc"
    chatbot.input = mock_prompt_session

    with contextlib.suppress(KeyboardInterrupt):
        chatbot.start_prompt(logger=None)

    console = Console(force_terminal=False)
    with console.capture() as capture:
        console.print(mock_sys_print.output)

    rendered_output = capture.get().strip()

    expected_output = (
        "Available contexts:\n\n"
        "default: I am an advanced AI language model designed to assist you with a wide range of tasks and provide helpful, clear, and accurate responses. My primary role is to serve as a chat assistant, engaging in natural, conversational dialogue, answering questions, generating ideas, and offering support across various topics.\n\n"
        "cli_helper: You are an expert for command line interface and know all common "
        "commands. Answer the command to execute as it without any explanation."
    )

    assert handle_output(rendered_output) == handle_output(expected_output)
