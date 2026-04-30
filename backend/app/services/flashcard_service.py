"""
Flashcard service v5 — NotebookLM-style.

SPEED TARGET: < 2 seconds (pre-generated cards are instant DB reads).

How it works:
1. After file upload, pregeneration.py creates LLM-quality flashcards in background
2. When user requests flashcards, we check if enough already exist (instant DB read)
3. If not enough, concept bank fills gaps (instant)
4. Real-time LLM only if both are empty (4s timeout)
"""
import re
import json
import random
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.flashcard import Flashcard
from app.models.syllabus import SyllabusTopic, SyllabusUnit
from app.models.upload import ContentChunk, Upload


# Leitner box intervals (in days)
LEITNER_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


# ────────────────────────────────────────────
#  Concept bank (instant, expert-written)
# ────────────────────────────────────────────

CONCEPT_FLASHCARDS = {
    "gradient": [
        ("What is the difference between Batch, Mini-batch, and Stochastic Gradient Descent?",
         "Batch GD uses the entire dataset per update, Mini-batch uses a subset, and SGD uses a single sample. Mini-batch is most common in practice as it balances noise and efficiency."),
        ("Why does SGD introduce noise, and how can this be beneficial?",
         "SGD uses one random sample per update, creating noisy gradient estimates. This noise can actually help escape local minima and saddle points, leading to better generalization."),
    ],
    "momentum": [
        ("How does momentum improve gradient descent?",
         "Momentum accumulates a velocity vector from past gradients, accelerating convergence in consistent directions and dampening oscillations. The typical coefficient is 0.9-0.99."),
        ("What's the difference between classical momentum and Nesterov?",
         "Classical computes gradient at current position then applies momentum. NAG looks ahead using momentum first, then computes gradient at the anticipated future position — providing a correction that improves convergence."),
    ],
    "adam": [
        ("How does the Adam optimizer work?",
         "Adam combines ideas from momentum (tracking mean of gradients) and RMSprop (tracking variance of gradients). It maintains per-parameter adaptive learning rates and includes bias correction for early training stability."),
    ],
    "dropout": [
        ("How does Dropout prevent overfitting?",
         "During training, neurons are randomly deactivated with probability p, forcing the network to develop redundant representations. At inference, all neurons are active but outputs are scaled by (1-p) to compensate."),
    ],
    "batch normalization": [
        ("What problem does Batch Normalization solve and how?",
         "BN addresses internal covariate shift — the change in layer input distributions during training. It normalizes each layer's inputs to zero mean and unit variance, then applies learnable scale (γ) and shift (β) parameters."),
    ],
    "activation": [
        ("Compare ReLU, sigmoid, and tanh activations.",
         "Sigmoid outputs [0,1] but suffers from vanishing gradients (max gradient 0.25). Tanh outputs [-1,1], is zero-centered but still vanishes. ReLU outputs max(0,x), has no vanishing gradient for positives but can 'die' for negatives."),
        ("What is the dying ReLU problem and how do Leaky ReLU and ELU solve it?",
         "Dying ReLU: neurons with consistently negative inputs output 0 and never recover. Leaky ReLU uses a small slope (e.g., 0.01x) for negatives. ELU uses α(e^x - 1) for negatives, giving smooth gradients and negative outputs."),
    ],
    "convolutional": [
        ("What makes CNNs effective for images compared to fully connected networks?",
         "CNNs use three key ideas: local connectivity (each neuron sees only a small region), parameter sharing (same filter everywhere), and translation equivariance. This dramatically reduces parameters while capturing spatial patterns."),
        ("How do you calculate the output size of a convolutional layer?",
         "Output = (Input - Filter + 2×Padding) / Stride + 1. For example, a 3×3 filter on 32×32 input with stride 1, padding 1 gives (32-3+2)/1+1 = 32×32."),
    ],
    "recurrent": [
        ("How do LSTMs solve the vanishing gradient problem in RNNs?",
         "LSTMs introduce a cell state that acts as a gradient highway. Three gates control information flow: forget gate (discard), input gate (store), output gate (reveal). Gradients flow through the cell state with only linear interactions."),
        ("What is the difference between LSTM and GRU?",
         "GRU merges the forget and input gates into a single 'update' gate and combines cell/hidden state, making it simpler with fewer parameters. LSTMs have 3 gates vs GRU's 2, but performance is often similar."),
    ],
    "transformer": [
        ("What is self-attention and why is it powerful?",
         "Self-attention computes relevance scores between all position pairs in a sequence using Q/K/V matrices. It captures long-range dependencies in O(1) path length (vs O(n) for RNNs) and processes all positions in parallel."),
        ("Why are positional encodings needed in Transformers?",
         "Transformers process all tokens simultaneously (no sequential processing like RNNs), so they have no inherent notion of order. Positional encodings (sinusoidal or learned) inject position information into the input embeddings."),
    ],
    "attention": [
        ("Why are dot products scaled by √(d_k) in attention?",
         "For large key dimensions d_k, dot products grow large in magnitude. This pushes softmax into regions where it has extremely small gradients, making learning difficult. Dividing by √(d_k) keeps values in a reasonable range."),
        ("What is multi-head attention and why use it?",
         "Multi-head attention runs multiple attention operations in parallel with different learned projections. Each head can attend to different aspects of the input (e.g., syntactic vs semantic relationships), enriching representations."),
    ],
    "gan": [
        ("How do GANs work and what is the training objective?",
         "A Generator creates fake data to fool a Discriminator, which tries to distinguish real from fake. They train adversarially in a minimax game. The Generator learns to produce increasingly realistic outputs."),
        ("What is mode collapse in GAN training?",
         "Mode collapse occurs when the Generator finds a few outputs that consistently fool the Discriminator and stops exploring the full data distribution, producing limited variety regardless of the input noise."),
    ],
    "autoencoder": [
        ("What is an autoencoder and what are its applications?",
         "An encoder compresses input into a latent representation, then a decoder reconstructs from it. The bottleneck forces learning meaningful features. Applications include denoising, anomaly detection, and dimensionality reduction."),
        ("How does a Variational Autoencoder (VAE) differ from a regular autoencoder?",
         "VAEs learn a probability distribution in latent space rather than fixed points. The encoder outputs mean and variance, and sampling uses the reparameterization trick. This enables smooth interpolation and generation of new samples."),
    ],
    "regularization": [
        ("Compare L1 and L2 regularization and when to use each.",
         "L1 (Lasso) adds |w| penalty → produces sparse models, useful for feature selection. L2 (Ridge) adds w² penalty → shrinks all weights toward zero. L1 pushes small weights to exactly zero; L2 makes weights small but rarely zero."),
    ],
    "segmentation": [
        ("What's the difference between semantic, instance, and panoptic segmentation?",
         "Semantic: labels every pixel with a class but doesn't distinguish instances. Instance: separates individual objects of the same class. Panoptic: combines both — labels every pixel AND distinguishes individual instances."),
    ],
    "yolo": [
        ("How does YOLO work and why is it fast?",
         "YOLO divides the image into an S×S grid. Each cell predicts B bounding boxes with confidence scores and C class probabilities — all in a single forward pass. This single-shot approach is much faster than two-stage detectors like R-CNN."),
    ],
    "resnet": [
        ("What are residual connections and what problem do they solve?",
         "Residual/skip connections add the input directly to the output: F(x) + x. This solves the degradation problem where deeper plain networks perform worse. Layers only need to learn the residual F(x), making identity mapping trivial."),
    ],
    "pooling": [
        ("What does pooling do and when to use max vs average pooling?",
         "Pooling reduces spatial dimensions, providing translation invariance and reducing computation. Max pooling selects the strongest activation (better for feature detection). Average pooling smooths features (often used in final layers)."),
    ],
    "vanishing": [
        ("Why do vanishing gradients occur and what are the solutions?",
         "With sigmoid/tanh, gradient ≤ 0.25 per layer. Through N layers: 0.25^N → vanishingly small. Solutions: ReLU activations, skip connections (ResNet), LSTM/GRU gates, batch normalization, careful weight initialization (He/Xavier)."),
    ],
    "boltzmann": [
        ("What is a Restricted Boltzmann Machine and how is it trained?",
         "An RBM is a two-layer undirected network (visible + hidden) with no intra-layer connections. Trained via contrastive divergence: alternate between positive phase (data-driven) and negative phase (model-driven) to approximate the gradient."),
    ],
    "unet": [
        ("What makes U-Net architecture effective for segmentation?",
         "U-Net has a symmetric encoder-decoder with skip connections that concatenate high-resolution feature maps from the encoder to the decoder at each level. This preserves fine spatial details crucial for pixel-accurate segmentation."),
    ],
    "sorting": [
        ("Compare the time/space complexity of major sorting algorithms.",
         "Quick Sort: avg O(n log n), worst O(n²), O(log n) space, in-place. Merge Sort: always O(n log n), O(n) space, stable. Heap Sort: always O(n log n), O(1) space. In practice, Quick Sort is fastest due to cache locality."),
    ],
    "graph": [
        ("When to use BFS vs DFS vs Dijkstra?",
         "BFS: shortest path in unweighted graphs, level-order traversal. DFS: cycle detection, topological sort, connected components. Dijkstra: shortest path with non-negative weights. All have O(V+E) complexity except Dijkstra O((V+E)log V)."),
    ],
    "dynamic programming": [
        ("What are the two key properties for dynamic programming?",
         "1) Optimal substructure: the optimal solution contains optimal sub-solutions. 2) Overlapping subproblems: the same subproblems are solved multiple times. DP caches these results (memoization or tabulation) to avoid redundant work."),
    ],
}


# ────────────────────────────────────────────
#  Fast LLM (real-time fallback, 4s timeout)
# ────────────────────────────────────────────

from app.services.llm_service import fast_llm_generate as _fast_llm_generate


# ────────────────────────────────────────────
#  Main generation pipeline
# ────────────────────────────────────────────

async def generate_flashcards_for_topic(
    topic_id: str,
    db: AsyncSession,
    count: int = 5,
) -> list[dict]:
    """Generate flashcards — instant from pre-generated + concept bank."""
    topic = await db.get(SyllabusTopic, topic_id)
    if not topic:
        return []

    # Get ALL existing fronts — NEVER repeat
    existing_result = await db.execute(
        select(Flashcard.front).where(Flashcard.topic_id == topic_id)
    )
    existing_fronts = set(r[0] for r in existing_result.all())

    # Check if we already have enough new cards available
    # (pre-generated by pregeneration.py in background after upload)
    if len(existing_fronts) >= count:
        # Cards already exist — no need to generate more
        return []

    needed = count
    new_cards = []

    # ── Step 1: Concept bank (INSTANT) ──
    topic_lower = topic.title.lower()
    bank_cards = _find_concept_flashcards(topic_lower, needed, existing_fronts)
    for front, back in bank_cards:
        if len(new_cards) >= needed:
            break
        if front not in existing_fronts:
            new_cards.append((front, back))
            existing_fronts.add(front)

    # ── Step 2: Fast LLM fallback (4s timeout) ──
    if len(new_cards) < needed:
        content = topic.content_cache or ""
        remaining = needed - len(new_cards)
        llm_cards = await _fast_llm_flashcards(topic.title, content, remaining, existing_fronts)
        for front, back in llm_cards:
            if len(new_cards) >= needed:
                break
            if front not in existing_fronts:
                new_cards.append((front, back))
                existing_fronts.add(front)

    # ── Save to DB ──
    saved = []
    for front, back in new_cards:
        card = Flashcard(
            topic_id=topic_id,
            front=front,
            back=back,
            leitner_box=1,
            next_review=datetime.utcnow(),
        )
        db.add(card)
        saved.append({"front": front, "back": back})

    await db.commit()
    return saved


async def _fast_llm_flashcards(
    topic_title: str, content: str, num: int, existing: set[str]
) -> list[tuple[str, str]]:
    """Try to generate flashcards via LLM with 4s timeout."""
    snippet = content[:600] if content else ""

    if snippet:
        prompt = f"""Generate {num} study flashcards about "{topic_title}" based on:
{snippet}

Each card: front = clear question testing understanding, back = concise answer (2-4 sentences).
JSON: [{{"front":"What is...?","back":"It is..."}}]"""
    else:
        prompt = f"""Generate {num} study flashcards about "{topic_title}".
Test understanding of concepts, definitions, applications, comparisons.
JSON: [{{"front":"What is...?","back":"It is..."}}]"""

    raw = await _fast_llm_generate(
        prompt=prompt,
        system="You are a professor creating study flashcards. Return ONLY a JSON array."
    )
    if not raw:
        return []

    return _parse_llm_flashcards(raw, existing)


def _parse_llm_flashcards(raw: str, existing: set[str]) -> list[tuple[str, str]]:
    """Parse LLM JSON output into flashcard pairs."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                items = json.loads(match.group())
            except json.JSONDecodeError:
                return []
        else:
            return []

    if not isinstance(items, list):
        return []

    cards = []
    for item in items:
        if not isinstance(item, dict):
            continue
        front = item.get("front", "").strip()
        back = item.get("back", "").strip()
        if not front or not back or front in existing:
            continue
        cards.append((front, back))
    return cards


def _find_concept_flashcards(topic_lower: str, needed: int, existing: set[str]) -> list[tuple[str, str]]:
    """Find matching flashcards from the curated concept bank."""
    candidates = []

    for keyword, card_list in CONCEPT_FLASHCARDS.items():
        if keyword in topic_lower:
            for front, back in card_list:
                if front not in existing:
                    candidates.append((front, back))

    if not candidates:
        for word in topic_lower.split():
            if len(word) < 4:
                continue
            for keyword, card_list in CONCEPT_FLASHCARDS.items():
                if word in keyword or keyword in word:
                    for front, back in card_list:
                        if front not in existing:
                            candidates.append((front, back))
                    break

    random.shuffle(candidates)
    return candidates[:needed]


# ────────────────────────────────────────────
#  Review & utility functions
# ────────────────────────────────────────────

async def review_flashcard(card_id: str, is_correct: bool, db: AsyncSession) -> dict:
    """Process a flashcard review — promote or demote in Leitner system."""
    card = await db.get(Flashcard, card_id)
    if not card:
        return {"error": "Card not found"}

    if is_correct:
        card.leitner_box = min(card.leitner_box + 1, 5)
    else:
        card.leitner_box = 1

    interval = LEITNER_INTERVALS[card.leitner_box]
    card.next_review = datetime.utcnow() + timedelta(days=interval)
    card.review_count += 1

    await db.commit()
    return {
        "card_id": card.id,
        "new_box": card.leitner_box,
        "next_review": card.next_review.isoformat(),
        "review_count": card.review_count,
    }


async def get_due_flashcards(subject_id: str, db: AsyncSession, limit: int = 20) -> list[dict]:
    """Get flashcards due for review, prioritizing lower boxes."""
    result = await db.execute(
        select(Flashcard)
        .join(SyllabusTopic)
        .join(SyllabusUnit)
        .where(
            SyllabusUnit.subject_id == subject_id,
            Flashcard.next_review <= datetime.utcnow(),
        )
        .order_by(Flashcard.leitner_box.asc(), Flashcard.next_review.asc())
        .limit(limit)
    )
    cards = result.scalars().all()
    return [
        {"id": c.id, "front": c.front, "back": c.back, "leitner_box": c.leitner_box,
         "review_count": c.review_count, "topic_id": c.topic_id}
        for c in cards
    ]


async def get_all_flashcards(subject_id: str, db: AsyncSession) -> list[dict]:
    """Get all flashcards for a subject."""
    result = await db.execute(
        select(Flashcard)
        .join(SyllabusTopic)
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
        .order_by(Flashcard.leitner_box.asc())
    )
    cards = result.scalars().all()
    return [
        {"id": c.id, "front": c.front, "back": c.back, "leitner_box": c.leitner_box,
         "next_review": c.next_review.isoformat() if c.next_review else None,
         "review_count": c.review_count, "topic_id": c.topic_id}
        for c in cards
    ]
