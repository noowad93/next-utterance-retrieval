import csv
from typing import List, Tuple

import torch
from pnlp.pipeline import NLPPipeline
from pnlp.text import Vocab
from torch.utils.data import Dataset


def load_dataset(file_path: str) -> List[List[str]]:
    reader = csv.reader(open(file_path))
    return list(reader)[1:]


class ConveRTTrainDataset(Dataset):
    def __init__(
        self, file_path: str, max_len: int, token_vocab: Vocab, pipeline: NLPPipeline,
    ):
        """데이터셋을 읽고, Model의 입력 형태로 변환해주는 Dataset입니다."""
        self.max_len = max_len
        self.token_vocab = token_vocab
        self.pipeline = pipeline
        self.training_instances = self._create_training_instances(file_path)

    def __len__(self) -> int:
        return len(self.training_instances)

    def __getitem__(self, key: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, int, int, int]:
        return self.training_instances[key]

    def _create_training_instances(
        self, file_path: str
    ) -> List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, int, int, int]]:
        """데이터셋의 경로를 받아 각 데이터를 Model의 입력 형태로 변환하여 리스트 형태로 반환해주는 함수입니다."""
        instances = []
        for line in load_dataset(file_path):
            if line[2] == "0":
                continue

            query = line[0].split("__eot__")[-2]
            context = line[0]
            reply = line[1]

            tokenized_query = self.pipeline.run(query)
            tokenized_context = self.pipeline.run(context)
            tokenized_reply = self.pipeline.run(reply)

            truncated_query = tokenized_query[-self.max_len :]
            truncated_context = tokenized_context[-self.max_len :]
            truncated_reply = tokenized_reply[: self.max_len]

            query_len = len(truncated_query)
            context_len = len(truncated_context)
            reply_len = len(truncated_reply)

            featurized_query = self.token_vocab.convert_tokens_to_ids(truncated_query)
            featurized_context = self.token_vocab.convert_tokens_to_ids(truncated_context)
            featurized_reply = self.token_vocab.convert_tokens_to_ids(truncated_reply)

            padded_query = featurized_query + [self.token_vocab.convert_token_to_id("<PAD>")] * (
                self.max_len - len(featurized_query)
            )
            padded_context = featurized_context + [self.token_vocab.convert_token_to_id("<PAD>")] * (
                self.max_len - len(featurized_context)
            )
            padded_reply = featurized_reply + [self.token_vocab.convert_token_to_id("<PAD>")] * (
                self.max_len - len(featurized_reply)
            )
            instances.append(
                (
                    torch.tensor(padded_query, dtype=torch.long),
                    torch.tensor(padded_context, dtype=torch.long),
                    torch.tensor(padded_reply, dtype=torch.long),
                    query_len,
                    context_len,
                    reply_len,
                )
            )
        return instances


class ConveRTEvalDataset(Dataset):
    def __init__(
        self, file_path: str, max_len: int, token_vocab: Vocab, pipeline: NLPPipeline,
    ):
        """데이터셋을 읽고, Model의 입력 형태로 변환해주는 Dataset입니다."""
        self.max_len = max_len
        self.token_vocab = token_vocab
        self.pipeline = pipeline
        self.eval_instances = self._create_eval_instances(file_path)

    def __len__(self) -> int:
        return len(self.eval_instances)

    def __getitem__(self, key: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.eval_instances[key]

    def _create_eval_instances(
        self, file_path: str
    ) -> List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, int, int, List[int]]]:
        """데이터셋의 경로를 받아 각 데이터를 Model의 입력 형태로 변환하여 리스트 형태로 반환해주는 함수입니다."""
        instances = [self._create_eval_single_instance(row) for row in load_dataset(file_path)]
        return instances

    def _create_eval_single_instance(
        self, line: List[str]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, int, int, List[int]]:
        query = line[0].split("__eot__")[-2]
        context = line[0]

        tokenized_query = self.pipeline.run(query)
        tokenized_context = self.pipeline.run(context)
        tokenized_candidates = [self.pipeline.run(candidate) for candidate in line[1:]]

        truncated_query = tokenized_query[-self.max_len :]
        truncated_context = tokenized_context[-self.max_len :]
        truncated_candidates = [tokenized_candidate[: self.max_len] for tokenized_candidate in tokenized_candidates]

        query_len = len(truncated_query)
        context_len = len(truncated_context)
        candidate_lens = [len(truncated_candidate) for truncated_candidate in truncated_candidates]

        featurized_query = self.token_vocab.convert_tokens_to_ids(truncated_query)
        featurized_context = self.token_vocab.convert_tokens_to_ids(truncated_context)
        featurized_candidates = [
            self.token_vocab.convert_tokens_to_ids(truncated_candidate) for truncated_candidate in truncated_candidates
        ]

        padded_query = featurized_query + [self.token_vocab.convert_token_to_id("<PAD>")] * (
            self.max_len - len(featurized_query)
        )
        padded_context = featurized_context + [self.token_vocab.convert_token_to_id("<PAD>")] * (
            self.max_len - len(featurized_context)
        )
        padded_candidates = [
            featurized_candidate
            + [self.token_vocab.convert_token_to_id("<PAD>")] * (self.max_len - len(featurized_candidate))
            for featurized_candidate in featurized_candidates
        ]
        return (
            torch.tensor(padded_query, dtype=torch.long),
            torch.tensor(padded_context, dtype=torch.long),
            torch.tensor(padded_candidates, dtype=torch.long),
            query_len,
            context_len,
            candidate_lens,
        )
