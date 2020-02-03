import logging
import sys

from pnlp.pipeline import NLPPipeline
from pnlp.text import Vocab
from pnlp.text.tokenizer import SpaceTokenizer
from pnlp.utils import TQDMHandler
from torch.utils.data import DataLoader, RandomSampler

from dssm_based_nsp.config import TrainConfig
from dssm_based_nsp.data import DSSMTrainDataset, DSSMEvalDataset
from dssm_based_nsp.model import DSSMModel, LSTMEncoderModel
from dssm_based_nsp.trainer import Trainer


def main():
    # Config
    config = TrainConfig()

    # Logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = TQDMHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
    logger.addHandler(handler)

    # Preparing for Utils (vocab, pipeline, label2idx)
    logger.info(f"get vocab from {config.vocab_file_path}")
    vocab = Vocab(config.vocab_file_path, "<UNK>")
    logger.info(f"create pipeline for normalizing and tokenizing")
    pipeline = NLPPipeline([SpaceTokenizer()])

    # Data for Training
    logger.info(f"prepare datasets for training")
    train_dataset = DSSMTrainDataset(config.train_file_path, config.max_seq_len, vocab, pipeline)
    random_sampler = RandomSampler(train_dataset)
    train_dataloader = DataLoader(
        train_dataset, sampler=random_sampler, batch_size=config.train_batch_size, drop_last=True
    )

    # Data for Evaluation
    logger.info(f"prepare datasets for evaluation")
    eval_dataset = DSSMEvalDataset(config.eval_file_path, config.max_seq_len, vocab, pipeline)
    eval_dataloader = DataLoader(eval_dataset, batch_size=config.eval_batch_size)

    # Preparing for Model
    logger.info(f"initialize the model")

    encoder_model = LSTMEncoderModel(len(vocab), config.word_embed_size, config.hidden_size, config.dropout_prob)
    dssm_model = DSSMModel(encoder_model)
    # Train
    trainer = Trainer(config, dssm_model, train_dataloader, eval_dataloader, logger)
    trainer.train()


if __name__ == "__main__":
    main()
