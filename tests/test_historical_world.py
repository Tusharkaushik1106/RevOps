from services.detector.schemas import ObservableInput
from services.detector.sequential import SequentialShadowEvaluator
from services.simulator.domain import IncidentType
from services.simulator.history import generate_evaluation, generate_history


def test_history_is_multi_day_and_deterministic():
    a = generate_history(3, 42, 100)
    b = generate_history(3, 42, 100)
    assert a.model_dump() == b.model_dump()
    assert len({p.timestamp.date() for p in a.payments}) == 3


def test_evaluation_incident_truth_is_separate():
    world = generate_evaluation(2, 42, IncidentType.ISSUER_DEGRADATION, 100)
    assert world.hidden_truth and not hasattr(world.history, "ground_truth")


def test_shadow_evaluator_is_sequential():
    world = generate_evaluation(2, 42, None, 100)
    history = ObservableInput(
        payments=[p.model_dump(mode="json") for p in world.history.payments], events=[]
    )
    evaluation = ObservableInput(
        payments=[p.model_dump(mode="json") for p in world.evaluation.payments], events=[]
    )
    observations = SequentialShadowEvaluator().run(history, evaluation)
    assert observations and observations[0].bucket_start <= observations[-1].bucket_start
