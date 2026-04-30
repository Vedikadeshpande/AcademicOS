"""
Question generation engine v7 — NotebookLM-style.

SPEED TARGET: < 2 seconds (pool serving is instant).

How it works:
1. After file upload, pregeneration.py creates LLM-quality questions → QuestionPool
2. When user requests a quiz, we pull from QuestionPool (instant DB read)
3. Concept bank fills any remaining gaps (instant)
4. Real-time LLM only if pool + bank are both empty (4s timeout)

Questions are comprehension-testing, not word-recall.
"""
import random
import re
import json
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.syllabus import SyllabusTopic, SyllabusUnit
from app.models.quiz import QuizQuestion, QuizSession, QuestionPool


# ────────────────────────────────────────────
#  Concept bank (instant, expert-written)
# ────────────────────────────────────────────

CONCEPT_QUESTIONS = {
    "gradient": [
        {"q": "In Stochastic Gradient Descent, what is used to estimate the gradient at each step?", "options": {"A": "A single randomly chosen training example", "B": "The entire training dataset", "C": "A fixed subset of validation data", "D": "The test dataset"}, "answer": "A", "explanation": "SGD uses one randomly chosen sample per update to estimate the gradient, introducing noise but enabling faster iterations."},
        {"q": "What typically happens when the learning rate is set too high?", "options": {"A": "The loss oscillates wildly or diverges", "B": "The model converges faster to the global minimum", "C": "Training takes longer but finds a better solution", "D": "The gradients become more stable"}, "answer": "A", "explanation": "A very high learning rate causes the optimizer to overshoot the minimum, making the loss oscillate or increase."},
        {"q": "What is the main disadvantage of Batch Gradient Descent compared to Mini-batch GD?", "options": {"A": "It is computationally expensive for large datasets", "B": "It introduces too much noise in gradient estimates", "C": "It cannot minimize convex functions", "D": "It requires a specific learning rate schedule"}, "answer": "A", "explanation": "Batch GD computes gradients over the entire dataset each step, making it slow and memory-intensive for large datasets."},
    ],
    "momentum": [
        {"q": "How does Nesterov Accelerated Gradient differ from standard momentum?", "options": {"A": "NAG computes the gradient at the anticipated future position of parameters", "B": "NAG uses a fixed momentum coefficient of 0.5", "C": "NAG does not use past gradients at all", "D": "NAG applies momentum only to the bias terms"}, "answer": "A", "explanation": "NAG first looks ahead by taking a step in the momentum direction, then computes the gradient at that future position, providing a correction factor."},
    ],
    "adam": [
        {"q": "Adam optimizer maintains two quantities for each parameter. What are they?", "options": {"A": "First moment (mean) and second moment (variance) of gradients", "B": "Learning rate and weight decay coefficient", "C": "Gradient magnitude and Hessian diagonal", "D": "Bias correction and momentum coefficient"}, "answer": "A", "explanation": "Adam tracks the exponentially decaying average of past gradients (1st moment) and past squared gradients (2nd moment) to adapt learning rates per parameter."},
        {"q": "What is the role of bias correction in Adam?", "options": {"A": "It compensates for the initialization bias of moment estimates toward zero", "B": "It prevents gradient explosion", "C": "It normalizes the learning rate", "D": "It applies L2 regularization"}, "answer": "A", "explanation": "Since the moment estimates are initialized to zero, they are biased toward zero early in training. Bias correction divides by (1-β^t) to compensate."},
    ],
    "dropout": [
        {"q": "During inference (testing), how are dropout-trained networks handled?", "options": {"A": "All neurons are active but outputs are scaled by the keep probability", "B": "Dropout is applied exactly as during training", "C": "Only the top-performing neurons are kept active", "D": "The network uses the average of multiple dropout masks"}, "answer": "A", "explanation": "At test time, all neurons are active. Outputs are scaled down by (1-p) to compensate for the fact that more neurons are active than during any single training pass."},
    ],
    "batch normalization": [
        {"q": "What problem does Batch Normalization primarily address?", "options": {"A": "Internal covariate shift — the change in layer input distributions during training", "B": "Overfitting on small datasets", "C": "The dying ReLU problem", "D": "Memory usage during backpropagation"}, "answer": "A", "explanation": "BN normalizes layer inputs to zero mean and unit variance, stabilizing training even with higher learning rates."},
    ],
    "activation": [
        {"q": "What is the 'dying ReLU' problem?", "options": {"A": "Neurons with consistently negative inputs always output 0 and stop learning permanently", "B": "ReLU outputs become unbounded and cause overflow", "C": "ReLU cannot be differentiated at zero", "D": "ReLU causes all weights to converge to the same value"}, "answer": "A", "explanation": "If a ReLU neuron gets stuck outputting 0 for all inputs, its gradient is always 0 and it can never recover."},
        {"q": "Why is ReLU generally preferred over sigmoid for hidden layers?", "options": {"A": "ReLU doesn't suffer from vanishing gradients for positive inputs and is computationally cheaper", "B": "ReLU always produces outputs between 0 and 1", "C": "ReLU has a smoother gradient than sigmoid", "D": "ReLU works better with small datasets"}, "answer": "A", "explanation": "Sigmoid's gradient is at most 0.25, causing vanishing gradients in deep networks. ReLU's gradient is 1 for positive inputs, allowing gradients to flow freely."},
    ],
    "convolutional": [
        {"q": "What is the purpose of padding in convolutional neural networks?", "options": {"A": "To preserve spatial dimensions and prevent loss of border information", "B": "To speed up computation by reducing filter size", "C": "To add noise for regularization", "D": "To normalize the input values"}, "answer": "A", "explanation": "Without padding, each convolution reduces spatial dimensions. Padding adds zeros around the input to maintain the original size and preserve edge information."},
        {"q": "Why do deeper layers of a CNN learn more abstract features?", "options": {"A": "Each successive layer combines features from previous layers, building higher-level representations", "B": "Deeper layers have more neurons and thus more capacity", "C": "Only deep layers apply non-linear activation functions", "D": "Shallow layers are frozen during training"}, "answer": "A", "explanation": "Early layers detect edges and textures. Middle layers combine these into parts. Deep layers recognize entire objects or complex concepts."},
    ],
    "recurrent": [
        {"q": "What is the primary mechanism by which LSTMs prevent the vanishing gradient problem?", "options": {"A": "The cell state provides a highway for gradients to flow unchanged across time steps", "B": "LSTMs use much larger learning rates than vanilla RNNs", "C": "LSTMs process sequences in reverse to shorten gradient paths", "D": "LSTMs use ReLU instead of tanh activations"}, "answer": "A", "explanation": "The cell state in an LSTM acts as a conveyor belt — information can flow through it with only linear interactions, preserving gradients."},
        {"q": "What are the three gates in an LSTM and what do they control?", "options": {"A": "Forget (discard old info), Input (store new info), Output (reveal info)", "B": "Forward, Backward, and Skip gates", "C": "Read, Write, and Reset gates", "D": "Attention, Memory, and Prediction gates"}, "answer": "A", "explanation": "The forget gate decides what to discard from the cell state, the input gate decides what new information to store, and the output gate decides what to reveal as the hidden state."},
    ],
    "transformer": [
        {"q": "Why is positional encoding necessary in Transformers?", "options": {"A": "Transformers process all tokens in parallel and have no inherent notion of sequence order", "B": "It helps reduce the number of attention heads needed", "C": "It replaces the need for multi-head attention", "D": "It compresses long sequences to fit in memory"}, "answer": "A", "explanation": "Unlike RNNs which process tokens sequentially, Transformers see all positions at once and need positional information added explicitly."},
    ],
    "attention": [
        {"q": "In scaled dot-product attention, why are dot products divided by √(d_k)?", "options": {"A": "To prevent dot products from growing too large, which would push softmax into regions with tiny gradients", "B": "To normalize the output to a probability distribution", "C": "To reduce the computational cost of matrix multiplication", "D": "To ensure all attention weights are positive"}, "answer": "A", "explanation": "For large d_k, dot products grow large in magnitude, causing softmax to output near-0 or near-1 values with vanishingly small gradients."},
    ],
    "gan": [
        {"q": "What is 'mode collapse' in GAN training?", "options": {"A": "The generator produces only a limited variety of outputs that fool the discriminator", "B": "The discriminator reaches 100% accuracy", "C": "Both networks' losses go to zero simultaneously", "D": "The generator copies training examples exactly"}, "answer": "A", "explanation": "Mode collapse occurs when the generator finds a few outputs that consistently fool the discriminator and stops exploring the full data distribution."},
    ],
    "autoencoder": [
        {"q": "What forces an autoencoder to learn meaningful features rather than copying the input?", "options": {"A": "The bottleneck layer has fewer dimensions than the input", "B": "A very low learning rate prevents memorization", "C": "Dropout is applied to the decoder only", "D": "The loss function penalizes exact reconstruction"}, "answer": "A", "explanation": "The bottleneck constrains the network to compress information, forcing it to learn the most important features and discard noise."},
    ],
    "regularization": [
        {"q": "Why does L1 regularization tend to produce sparse models?", "options": {"A": "The L1 penalty's gradient has constant magnitude, pushing small weights exactly to zero", "B": "L1 regularization is computationally cheaper than L2", "C": "L1 forces all weights to be positive", "D": "L1 only penalizes the largest weights"}, "answer": "A", "explanation": "L1's gradient is ±λ regardless of weight magnitude. For small weights, this constant push is enough to zero them out, creating sparsity."},
    ],
    "segmentation": [
        {"q": "What is the key difference between semantic segmentation and instance segmentation?", "options": {"A": "Semantic assigns class labels to pixels; instance also distinguishes between separate objects of the same class", "B": "Semantic segmentation works only on videos", "C": "Instance segmentation does not use neural networks", "D": "They produce identical output with different computational costs"}, "answer": "A", "explanation": "Semantic segmentation labels every pixel with a class. Instance segmentation goes further by separating individual object instances within the same class."},
    ],
    "yolo": [
        {"q": "What makes YOLO fundamentally different from R-CNN based detectors?", "options": {"A": "YOLO processes the entire image in a single forward pass, treating detection as regression", "B": "YOLO uses more accurate region proposals", "C": "YOLO can only detect one class of objects", "D": "YOLO requires pre-trained feature extractors"}, "answer": "A", "explanation": "YOLO divides the image into a grid and predicts bounding boxes and class probabilities in one pass. R-CNN uses a two-stage approach with region proposals."},
    ],
    "resnet": [
        {"q": "What problem do skip connections in ResNet solve?", "options": {"A": "The degradation problem — deeper plain networks perform worse despite having more capacity", "B": "They reduce the total number of trainable parameters", "C": "They eliminate the need for any activation functions", "D": "They make batch normalization unnecessary"}, "answer": "A", "explanation": "Without skip connections, very deep networks suffer from degradation where performance decreases. Skip connections let layers learn residuals F(x), making it easy to learn identity mappings."},
    ],
    "pooling": [
        {"q": "Why is max pooling preferred over average pooling in most CNN architectures?", "options": {"A": "Max pooling captures the strongest activations, providing better feature selection", "B": "Max pooling preserves all spatial information completely", "C": "Average pooling cannot reduce spatial dimensions", "D": "Max pooling uses fewer parameters than average pooling"}, "answer": "A", "explanation": "Max pooling selects the maximum activation in each receptive field region, effectively highlighting the most prominent detected features."},
    ],
    "vanishing": [
        {"q": "Why does the vanishing gradient problem occur in deep networks with sigmoid activations?", "options": {"A": "Sigmoid's maximum gradient is 0.25, so multiplying many such values through layers makes gradients exponentially small", "B": "Sigmoid always outputs zero for negative inputs", "C": "Deep networks have too many parameters for sigmoid to handle", "D": "Sigmoid is not continuous and cannot be differentiated"}, "answer": "A", "explanation": "The maximum gradient of sigmoid is 0.25 (at x=0). Backpropagating through N layers multiplies these small values, giving gradients of order 0.25^N."},
    ],
    "boltzmann": [
        {"q": "What is the key characteristic of a Restricted Boltzmann Machine (RBM)?", "options": {"A": "No connections exist between neurons in the same layer — only between visible and hidden layers", "B": "All neurons are fully connected to all other neurons", "C": "RBMs can only process binary data", "D": "RBMs require labeled training data"}, "answer": "A", "explanation": "The 'restricted' in RBM means no intra-layer connections exist, making efficient training via contrastive divergence possible."},
    ],
    "unet": [
        {"q": "What is U-Net's defining architectural feature?", "options": {"A": "Symmetric encoder-decoder with skip connections that concatenate feature maps between corresponding levels", "B": "A single continuous pathway without any skip connections", "C": "It uses only 1×1 convolutions for efficiency", "D": "It was specifically designed for image classification tasks"}, "answer": "A", "explanation": "U-Net's skip connections concatenate high-resolution features from the encoder to the decoder at each level, enabling precise spatial localization."},
    ],
    "sorting": [
        {"q": "What gives Quick Sort its practical speed advantage despite O(n²) worst case?", "options": {"A": "Excellent cache locality and low constant factors in the average O(n log n) case", "B": "It always avoids the worst case with random pivots", "C": "It uses less memory than all other sorting algorithms", "D": "It performs fewer comparisons than Merge Sort in every case"}, "answer": "A", "explanation": "Quick Sort's in-place partitioning has excellent cache performance. With good pivot selection, the worst case is extremely rare in practice."},
    ],
    "graph": [
        {"q": "Why can't Dijkstra's algorithm handle negative edge weights?", "options": {"A": "It greedily finalizes nodes and assumes no shorter path exists later — negative edges violate this", "B": "It cannot store negative numbers in its priority queue", "C": "Negative weights make the graph always contain cycles", "D": "Dijkstra's only works on directed acyclic graphs"}, "answer": "A", "explanation": "Dijkstra marks nodes as 'done' when first dequeued. A negative edge could provide a shorter path through an already-finalized node."},
    ],
    "dynamic programming": [
        {"q": "What distinguishes dynamic programming from divide-and-conquer?", "options": {"A": "DP solves overlapping subproblems and caches results; divide-and-conquer solves independent subproblems", "B": "DP always runs in polynomial time", "C": "Divide-and-conquer cannot use recursion", "D": "DP requires the problem to have a closed-form solution"}, "answer": "A", "explanation": "Both decompose problems. DP's key insight is that subproblems overlap — caching prevents redundant recomputation."},
    ],
}


# ────────────────────────────────────────────
#  Fast LLM (real-time fallback, 4s timeout)
# ────────────────────────────────────────────

from app.services.llm_service import fast_llm_generate as _fast_llm_generate


# ────────────────────────────────────────────
#  Main generation pipeline
# ────────────────────────────────────────────

RECENT_WINDOW_DAYS = 7


async def generate_questions(
    subject_id: str,
    db: AsyncSession,
    num_questions: int = 10,
    question_type: str = "mixed",
    difficulty: str = "medium",
    topic_ids: list[str] = None,
    marks_per_question: int = 0,
) -> list[dict]:
    """Generate quiz questions — instant from pre-generated pool."""

    # Get topics
    if topic_ids:
        result = await db.execute(
            select(SyllabusTopic, SyllabusUnit.title)
            .join(SyllabusUnit)
            .where(SyllabusTopic.id.in_(topic_ids))
        )
    else:
        result = await db.execute(
            select(SyllabusTopic, SyllabusUnit.title)
            .join(SyllabusUnit)
            .where(SyllabusUnit.subject_id == subject_id)
        )
    rows = result.all()
    if not rows:
        return []

    # Recently-asked questions (7 day dedup window)
    cutoff = datetime.utcnow() - timedelta(days=RECENT_WINDOW_DAYS)
    try:
        recent_result = await db.execute(
            select(QuizQuestion.question_text)
            .join(QuizSession)
            .where(QuizSession.subject_id == subject_id, QuizSession.taken_at >= cutoff)
        )
        used_questions = set(r[0] for r in recent_result.all() if r[0])
    except Exception:
        used_questions = set()

    topic_ids_list = [t.id for t, _ in rows]
    all_questions = []
    pool_questions = []
    marks = marks_per_question if marks_per_question > 0 else 1

    # ── Step 1: Pull from QuestionPool (INSTANT) ──
    try:
        pool_result = await db.execute(
            select(QuestionPool)
            .where(
                QuestionPool.topic_id.in_(topic_ids_list),
            )
            .order_by(QuestionPool.created_at.desc())
        )
        pool_questions = pool_result.scalars().all()

        for pq in pool_questions:
            if len(all_questions) >= num_questions:
                break
            if pq.question_text in used_questions:
                continue

            all_questions.append({
                "question_text": pq.question_text,
                "question_type": "mcq",
                "correct_answer": pq.correct_answer,
                "options": pq.options,
                "explanation": pq.explanation or "",
                "topic_id": pq.topic_id,
                "topic_title": next((t.title for t, _ in rows if t.id == pq.topic_id), ""),
                "marks": marks,
            })
            used_questions.add(pq.question_text)

        await db.commit()
    except Exception as e:
        print(f"[QuizGen] Pool read error: {e}")

    # ── Step 2: Concept bank for remaining gaps (INSTANT) ──
    if len(all_questions) < num_questions:
        topics_subset = [(t, ut) for t, ut in rows]
        random.shuffle(topics_subset)
        
        for topic, unit_title in topics_subset:
            if len(all_questions) >= num_questions:
                break
            
            needed = num_questions - len(all_questions)
            bank_qs = _find_concept_questions(topic.title, needed, used_questions)
            for q in bank_qs:
                q["topic_id"] = topic.id
                q["topic_title"] = topic.title
                q["marks"] = marks
                used_questions.add(q["question_text"])
                all_questions.append(q)

    # ── Step 3: Real-time LLM for any remaining gaps ──
    # Use longer timeout (15s) when pool+bank were both empty
    if len(all_questions) < num_questions:
        remaining = num_questions - len(all_questions)
        is_last_resort = len(all_questions) == 0  # pool + bank produced nothing
        timeout = 15.0 if is_last_resort else 4.0
        
        # Try each topic until we have enough
        topics_to_try = [(t, ut) for t, ut in rows]
        random.shuffle(topics_to_try)
        
        llm_attempts = 0
        max_llm_attempts = 3
        
        for topic, unit_title in topics_to_try:
            if len(all_questions) >= num_questions or llm_attempts >= max_llm_attempts:
                break
            
            still_needed = num_questions - len(all_questions)
            content = topic.content_cache or ""
            snippet = content[:600] if content else ""
            
            template_str = 'JSON: [{"question":"...","options":{"A":"...","B":"...","C":"...","D":"..."},"correct":"A","explanation":"..."}]'
            if question_type == "short":
                 template_str = 'JSON: [{"question":"...", "correct_answer":"...", "explanation":"..."}]'
                 prompt_text = f'Generate {still_needed} high-quality short answer questions about "{topic.title}"'
            else:
                 prompt_text = f'Generate {still_needed} high-quality MCQs about "{topic.title}" with 4 options.'
                 
            if snippet:
                prompt = f'{prompt_text} based on this material:\n{snippet}\n{template_str}'
            else:
                prompt = f'{prompt_text} Questions should test comprehension.\n{template_str}'

            raw = await _fast_llm_generate(
                prompt=prompt, 
                system="You are a professor. Generate exam MCQs in JSON. Return ONLY a JSON array."
            )
            llm_attempts += 1
            
            if not raw:
                # LLM failed or timed out. Stop hitting it immediately to avoid endless loading.
                break
                
            llm_qs = _parse_llm_questions(raw, used_questions)
            if not llm_qs:
                # If everything was filtered out as 'used', ignore the filter so we don't return an empty quiz
                llm_qs = _parse_llm_questions(raw, set())
                
            for q in llm_qs:
                if len(all_questions) >= num_questions:
                    break
                q["topic_id"] = topic.id
                q["topic_title"] = topic.title
                q["marks"] = marks
                all_questions.append(q)
        
        # If this was a last resort, trigger pre-generation in background for next time
        if is_last_resort and rows:
            try:
                import asyncio
                from app.services.pregeneration import pregenerate_for_subject
                unit_result = await db.execute(
                    select(SyllabusUnit.subject_id)
                    .where(SyllabusUnit.id == rows[0][0].unit_id)
                )
                sid = unit_result.scalar_one_or_none()
                if sid:
                    asyncio.create_task(pregenerate_for_subject(sid))
            except Exception:
                pass

    # ── Step 4: Recycle used questions if needed ──
    # If LLM generation failed and we still don't have enough questions,
    # pull from previously used pool questions rather than failing the quiz.
    if len(all_questions) < num_questions and pool_questions:
        active_question_texts = {q['question_text'] for q in all_questions}
        for pq in pool_questions:
            if len(all_questions) >= num_questions:
                break
            if pq.question_text not in active_question_texts:
                all_questions.append({
                    "question_text": pq.question_text,
                    "question_type": "mcq",
                    "correct_answer": pq.correct_answer,
                    "options": pq.options,
                    "explanation": pq.explanation or "",
                    "topic_id": pq.topic_id,
                    "topic_title": next((t.title for t, _ in rows if t.id == pq.topic_id), ""),
                    "marks": marks,
                })
                active_question_texts.add(pq.question_text)

    # ── Step 5: Last resort, recycle from past quizzes ──
    # If the pool was completely empty and LLM timed out, we might still have questions from old quizzes!
    if len(all_questions) < num_questions:
        try:
            active_question_texts = {q['question_text'] for q in all_questions}
            past_result = await db.execute(
                select(QuizQuestion)
                .join(QuizSession)
                .where(
                    QuizSession.subject_id == subject_id,
                    QuizQuestion.topic_id.in_(topic_ids_list)
                )
                .order_by(QuizSession.taken_at.desc())
            )
            past_questions = past_result.scalars().all()
            for pq in past_questions:
                if len(all_questions) >= num_questions:
                    break
                if pq.question_text not in active_question_texts:
                    all_questions.append({
                        "question_text": pq.question_text,
                        "question_type": pq.question_type,
                        "correct_answer": pq.correct_answer,
                        "options": pq.options,
                        "explanation": "", # past quiz questions don't store explanation
                        "topic_id": pq.topic_id,
                        "topic_title": next((t.title for t, _ in rows if t.id == pq.topic_id), ""),
                        "marks": pq.marks,
                    })
                    active_question_texts.add(pq.question_text)
        except Exception as e:
            print(f"[QuizGen] Past quiz recycle error: {e}")

    random.shuffle(all_questions)
    return all_questions[:num_questions]


def _parse_llm_questions(raw: str, used: set[str]) -> list[dict]:
    """Parse LLM JSON output into question dicts."""
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

    questions = []
    for item in items:
        if not isinstance(item, dict):
            continue
        q_text = item.get("question", "").strip()
        if not q_text or q_text in used:
            continue
            
        options = item.get("options", {})
        correct = item.get("correct", "A").strip().upper()
        
        if options and isinstance(options, dict) and len(options) >= 2:
            if correct not in options:
                correct = list(options.keys())[0]
            questions.append({
                "question_text": q_text,
                "question_type": "mcq",
                "correct_answer": correct,
                "options": json.dumps(options),
                "explanation": item.get("explanation", ""),
            })
        elif "correct_answer" in item or "explanation" in item:
            # Short answer format
            ca = item.get("correct_answer", item.get("explanation", ""))
            expl = item.get("explanation", ca)
            # Encode correctly as JSON string for the DB format in Viva
            ca_json = json.dumps({"hint": ca, "keywords": []})
            questions.append({
                "question_text": q_text,
                "question_type": "short",
                "correct_answer": ca_json,
                "options": None,
                "explanation": expl,
            })
    return questions


def _find_concept_questions(topic_title: str, needed: int, used: set[str]) -> list[dict]:
    """Find matching questions from the hardcoded concept bank."""
    topic_lower = topic_title.lower()
    candidates = []
    
    for keyword, qlist in CONCEPT_QUESTIONS.items():
        if keyword in topic_lower:
            candidates.extend(qlist)

    if not candidates:
        for word in topic_lower.split():
            if len(word) < 4:
                continue
            for keyword, qlist in CONCEPT_QUESTIONS.items():
                if word in keyword or keyword in word:
                    candidates.extend(qlist)

    if not candidates:
        return []

    random.shuffle(candidates)
    results = []
    for item in candidates:
        if len(results) >= needed:
            break
        if item["q"] in used:
            continue
        results.append({
            "question_text": item["q"],
            "question_type": "mcq",
            "correct_answer": item["answer"],
            "options": json.dumps(item["options"]),
            "explanation": item.get("explanation", ""),
        })
    return results


async def generate_mock_paper(
    subject_id: str,
    db: AsyncSession,
    marking_scheme: list[dict] = None,
) -> list[dict]:
    """Generate a mock exam paper."""
    if not marking_scheme:
        marking_scheme = [{"marks": 1, "count": 20, "type": "mcq"}]

    all_questions = []
    for scheme in marking_scheme:
        qs = await generate_questions(
            subject_id, db,
            num_questions=scheme["count"],
            question_type=scheme["type"],
            marks_per_question=scheme["marks"],
        )
        all_questions.extend(qs)
    return all_questions


async def generate_exam_paper(
    subject_id: str,
    db: AsyncSession,
    exam_type: str = "end_sem"  # "mid_sem" or "end_sem"
) -> list[dict]:
    """Generate a structured exam paper using Bloom's Taxonomy."""
    
    # 1. Fetch topics and snippet content
    result = await db.execute(
        select(SyllabusTopic, SyllabusUnit.title)
        .join(SyllabusUnit)
        .where(SyllabusUnit.subject_id == subject_id)
    )
    rows = result.all()
    topic_summaries = []
    topics_dict = {}

    if not rows:
        # Fallback: No syllabus topics. Try fetching raw content chunks from any uploaded files (pdfs, ppts, pyqs)
        from app.models.upload import Upload, ContentChunk
        chunks_res = await db.execute(
            select(ContentChunk.content)
            .join(Upload)
            .where(Upload.subject_id == subject_id)
            .limit(20)
        )
        raw_chunks = chunks_res.scalars().all()
        if not raw_chunks:
            return []  # Honestly no data is available for this subject at all!
        for i, c in enumerate(raw_chunks):
            topic_summaries.append(f"Content Extract {i+1}: {c[:400].strip()}")
    else:
        for topic, unit_title in rows:
            topics_dict[topic.id] = topic
            content = (topic.content_cache or "")[:400]
            topic_summaries.append(f"Topic: {topic.title} (Unit: {unit_title}) - {content.strip()}")

    # 2. Define schema based on exam type
    if exam_type == "mid_sem":
        # Mid-sem (30 marks): 5x2m, 3x4m, 1x8m
        schema_text = "Mid-sem Exam (Total 30 Marks): 5 questions of 2 marks, 3 questions of 4 marks, and 1 question of 8 marks."
    else:
        # End-sem (80 marks): 10x2m, 4x4m, 3x8m, 1x20m = 80 Total
        schema_text = "End-sem Exam (Total 80 Marks): 10 questions of 2 marks, 4 questions of 4 marks, 3 questions of 8 marks, and 1 question of 20 marks."

    # 3. Create context string (limit to 20 topics to stay within context windows)
    random.shuffle(topic_summaries)
    context = "\\n".join(topic_summaries[:20])

    # 4. Prompt construction using Bloom's Taxonomy
    system_prompt = "You are a senior university professor. Generate exam paper questions in JSON. Return ONLY a JSON array."
    prompt = f"""Generate a university exam paper based on the following syllabus content.
Make sure the questions evaluate students using Bloom's Taxonomy (e.g., Remember, Understand, Apply, Analyze, Evaluate, Create).
The questions must be highly relevant, realistic, make sense, and be diverse in structure. Do not just output rubbish.
Format requirements: {schema_text}
Mixed types (short answer for 2/4 markers, long answer/essay for 8/20 markers). Do not include any MCQ questions.

Content:
{context}

Respond strictly with ONLY a JSON array where each object has:
- `question`: The text of the question
- `marks`: The marks allocated (e.g., 2, 4, 8, or 20)
- `question_type`: 'short' or 'long'
- `bloom_level`: e.g., 'Analyze'
- `hint`: A short guidance/hint for the correct answer

Make sure to EXACTLY match the number of questions and marks specified in the format requirements.
"""

    # 5. Fast LLM call
    try:
        raw = await _fast_llm_generate(prompt=prompt, system=system_prompt, max_tokens=3500)
    except Exception as e:
        print(f"[QuizGen] Exception in LLM exam generation: {e}")
        raw = ""

    # 6. Parse
    items = []
    if raw:
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
                    pass

    topic_ids_list = list(topics_dict.keys())
    
    # --- FALLBACK LOGIC ---
    if not items:
        print("[QuizGen] LLM failed for exam paper, using fallback logic.")
        target_marks = [2]*5 + [4]*3 + [8]*1 if exam_type == "mid_sem" else [2]*10 + [4]*4 + [8]*3 + [20]*1
        
        # Try database first
        try:
            pool_result = await db.execute(
                select(QuestionPool)
                .where(QuestionPool.topic_id.in_(topic_ids_list))
                .order_by(QuestionPool.created_at.desc())
                .limit(len(target_marks))
            )
            db_qs = pool_result.scalars().all()
        except Exception:
            db_qs = []
            
        db_qs_cycle = db_qs * (len(target_marks) // len(db_qs) + 1) if db_qs else []
        db_idx = 0

        for m in target_marks:
            tid = random.choice(topic_ids_list)
            t_title = topics_dict[tid].title
            
            if db_qs_cycle and db_idx < len(db_qs_cycle):
                q_text = db_qs_cycle[db_idx].question_text
                # Convert DB question (likely MCQ) to subjective by stripping options if needed
                if q_text.endswith("?"):
                    pass
                else:
                    q_text += " Explain."
                db_idx += 1
            else:
                if m <= 2:
                    bloom = random.choice(["Remember", "Understand"])
                    q_text = random.choice([
                        f"Define the core concept of {t_title} and state one major application.",
                        f"Identify and briefly outline the primary characteristics of {t_title}.",
                        f"Recall the main definition of {t_title}. Why is it relevant?",
                    ])
                elif m == 4:
                    bloom = random.choice(["Understand", "Apply"])
                    q_text = random.choice([
                        f"Explain how {t_title} operates in a real-world scenario.",
                        f"Demonstrate the typical use-case for {t_title}. What problems does it solve?",
                        f"Compare the theoretical concept of {t_title} with a practical implementation.",
                    ])
                elif m == 8:
                    bloom = random.choice(["Analyze", "Evaluate"])
                    q_text = random.choice([
                        f"Critically analyze the significance of {t_title}. Break down its sub-components and evaluate their individual impact.",
                        f"Discuss the advantages and limitations of {t_title}. Under what circumstances would it fail?",
                        f"Examine a complex scenario involving {t_title}. How would you optimize its performance?",
                    ])
                else: # 20 marks
                    bloom = "Create"
                    q_text = random.choice([
                        f"Design a comprehensive system architecture that fundamentally relies on {t_title}. Justify each of your design choices.",
                        f"Synthesize the various principles of {t_title} to propose a novel solution to an industry problem.",
                        f"Evaluate the evolution of {t_title}. Formulate how future developments might reshape its use cases entirely.",
                    ])

            items.append({
                "question": q_text,
                "marks": m,
                "question_type": "short" if m <= 4 else "long",
                "bloom_level": bloom if not (db_qs_cycle and db_idx - 1 < len(db_qs_cycle)) else "Understand",
                "hint": f"Consider key principles of {t_title}.",
                "topic_id": tid,
                "topic_title": t_title
            })

    all_questions = []
    for item in items:
        if not isinstance(item, dict):
            continue
            
        tid = item.get("topic_id")
        if not tid and topic_ids_list:
            tid = random.choice(topic_ids_list)
            
        q_text = item.get("question", "")
        marks = int(item.get("marks", 2))
        q_type = item.get("question_type", "short")
        hint = item.get("hint", "")
        
        # Format correct answer to hold hint and bloom
        bloom = item.get("bloom_level", "Understand")
        ca_json = json.dumps({"hint": f"[{bloom}] {hint}", "keywords": []})
        
        t_title = item.get("topic_title")
        if not t_title and tid and tid in topics_dict:
            t_title = topics_dict[tid].title
        if not t_title:
            t_title = "General Content"
            
        all_questions.append({
            "question_text": q_text,
            "question_type": q_type,
            "correct_answer": ca_json,
            "options": None,
            "explanation": f"Bloom's Taxonomy Level: {bloom}",
            "topic_id": tid,
            "topic_title": t_title,
            "marks": marks,
        })

    return all_questions
