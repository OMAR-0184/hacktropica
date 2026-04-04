from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal


# ── Auth (JSON login) ────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


# ── Learning Requests ─────────────────────────────────────────

class LearningRequest(BaseModel):
    topic: str
    course_mode: str = "detailed"  # "detailed" or "micro"
    traversal_mode: Literal["bfs", "dfs"] = "dfs"


class EvaluateRequest(BaseModel):
    answers: List[int]  # Selected option index per question


class NextRequest(BaseModel):
    selected_node: Optional[str] = None
    traversal_mode: Optional[Literal["bfs", "dfs"]] = None


class ContinueRequest(BaseModel):
    answers: Optional[List[int]] = None
    selected_node: Optional[str] = None
    traversal_mode: Optional[Literal["bfs", "dfs"]] = None
    client_request_id: Optional[str] = None


class GraphNodeCreateRequest(BaseModel):
    node_id: str = Field(..., min_length=1, max_length=160)
    parent_node_id: Optional[str] = None
    node_kind: Literal["concept", "advanced", "remediation"] = "concept"
    is_math_heavy: Optional[bool] = None
    add_to_frontier: bool = True


class QuizQuestion(BaseModel):
    question_id: str
    question: str
    options: List[str]


class QuizResponse(BaseModel):
    session_id: str
    node_id: str
    questions: List[QuizQuestion]
    question_count: int = 0
    numerical_target_ratio: float = 0.0
    actual_numerical_ratio: float = 0.0


class NodeHierarchyMeta(BaseModel):
    node_id: str
    parent_node_id: Optional[str] = None
    depth: Optional[int] = None
    node_kind: Optional[str] = None
    path_from_root: List[str] = []
    is_math_heavy: Optional[bool] = None
    is_expanded: Optional[bool] = None
    status: Optional[str] = None
    score: Optional[float] = None
    attempts: Optional[int] = None


# ── Tutor / Curator typed content ─────────────────────────────

class TutorContent(BaseModel):
    learning_objective: str = ""
    explanation: str = ""
    examples: List[str] = []
    common_misconception: str = ""
    practice_task: str = ""
    code_snippet: Optional[str] = None


class CuratorResource(BaseModel):
    title: str = ""
    url: str = ""
    description: Optional[str] = None


class CuratorContent(BaseModel):
    articles: List[CuratorResource] = []
    videos: List[CuratorResource] = []
    courses: List[CuratorResource] = []
    references: List[str] = []


# ── Responses ─────────────────────────────────────────────────

class StartResponse(BaseModel):
    session_id: str
    message: str


class LessonResponse(BaseModel):
    session_id: str
    node_id: Optional[str] = None
    tutor_content: Optional[TutorContent] = None
    curator_content: Optional[CuratorContent] = None
    is_remediation: bool = False
    parent_node_id: Optional[str] = None
    depth: Optional[int] = None
    node_kind: Optional[str] = None
    path_from_root: List[str] = []
    is_math_heavy: Optional[bool] = None
    is_expanded: Optional[bool] = None


class EvaluateResponse(BaseModel):
    status: str
    message: str


class JourneyChoicesResponse(BaseModel):
    session_id: str
    current_node: str = ""
    traversal_mode: Literal["bfs", "dfs"] = "dfs"
    options: List[str] = []
    waiting_on: List[str] = []
    journey_mode: Literal["learn", "review"] = "learn"
    can_go_back: bool = False
    previous_node: Optional[str] = None
    recommended_node: Optional[str] = None
    recommendation_reason: Optional[str] = None
    recommendation_factors: Dict[str, Any] = {}
    parent_node_id: Optional[str] = None
    depth: Optional[int] = None
    node_kind: Optional[str] = None
    path_from_root: List[str] = []
    is_math_heavy: Optional[bool] = None
    is_expanded: Optional[bool] = None
    option_metadata: Dict[str, Dict[str, Any]] = {}


class JourneyNextActionResponse(BaseModel):
    session_id: str
    action: str
    status: str
    message: str
    current_node: str = ""
    waiting_on: List[str] = []
    options: List[str] = []
    traversal_mode: Literal["bfs", "dfs"] = "dfs"
    journey_mode: Literal["learn", "review"] = "learn"
    can_go_back: bool = False
    previous_node: Optional[str] = None
    recommended_node: Optional[str] = None
    recommendation_reason: Optional[str] = None
    recommendation_factors: Dict[str, Any] = {}
    required_input: Optional[str] = None
    parent_node_id: Optional[str] = None
    depth: Optional[int] = None
    node_kind: Optional[str] = None
    path_from_root: List[str] = []
    is_math_heavy: Optional[bool] = None
    is_expanded: Optional[bool] = None
    option_metadata: Dict[str, Dict[str, Any]] = {}


class ContinueResponse(BaseModel):
    session_id: str
    status: str
    action: str
    message: str
    enqueued: bool = False
    journey_mode: Literal["learn", "review"] = "learn"
    can_go_back: bool = False
    previous_node: Optional[str] = None
    options: List[str] = []
    recommended_node: Optional[str] = None
    recommendation_reason: Optional[str] = None
    recommendation_factors: Dict[str, Any] = {}
    required_input: Optional[str] = None
    request_status: Optional[Literal["accepted", "duplicate", "in_progress"]] = None
    request_id: Optional[str] = None
    parent_node_id: Optional[str] = None
    depth: Optional[int] = None
    node_kind: Optional[str] = None
    path_from_root: List[str] = []
    is_math_heavy: Optional[bool] = None
    is_expanded: Optional[bool] = None
    option_metadata: Dict[str, Dict[str, Any]] = {}


class QuestionResult(BaseModel):
    question_id: str
    question: str
    options: List[str]
    correct_index: int
    user_index: int
    is_correct: bool


class EvaluationResult(BaseModel):
    """Structured evaluation result returned by GET /evaluation."""
    score: float = Field(..., description="Float between 0 and 1 representing mastery")
    weak_areas: List[str] = Field(..., description="Concepts the user struggled with")
    feedback: str = Field(..., description="Qualitative feedback explaining to the user why they received their score.")
    passed: bool = Field(..., description="True if score >= mastery_threshold")
    next_action: str = Field(..., description="'next_topic' or 'remediation' | 'completed' | 'pending'")
    question_results: List[QuestionResult] = Field(default_factory=list, description="Per-question deterministic grading details.")
    question_count: int = 0
    numerical_target_ratio: float = 0.0
    actual_numerical_ratio: float = 0.0


class SubtopicProgress(BaseModel):
    name: str
    status: str = "locked"  # locked | unlocked | active | mastered
    score: Optional[float] = None
    attempts: int = 0
    parent_node_id: Optional[str] = None
    depth: Optional[int] = None
    node_kind: Optional[str] = None
    path_from_root: List[str] = []
    is_math_heavy: Optional[bool] = None
    is_expanded: Optional[bool] = None


class ProgressResponse(BaseModel):
    session_id: str
    topic: str
    status: str = "active"
    subtopics: List[SubtopicProgress] = []
    current_node: str = ""
    overall_progress: float = 0.0  # 0.0–1.0
    completed_count: int = 0
    total_count: int = 0
    history: List[Dict[str, Any]] = []
    traversal_mode: Literal["bfs", "dfs"] = "dfs"
    active_frontier: List[str] = []
    current_path: List[str] = []
    children_map: Dict[str, List[str]] = {}
    node_catalog: List[NodeHierarchyMeta] = []


class WorkflowSnapshotResponse(BaseModel):
    session_id: str
    status: str
    current_phase: Optional[str] = None
    topic: str = ""
    current_node: str = ""
    journey_mode: Literal["learn", "review"] = "learn"
    traversal_mode: Literal["bfs", "dfs"] = "dfs"
    waiting_on: List[str] = []
    next_action: Optional[str] = None
    options: List[str] = []
    recommended_node: Optional[str] = None
    recommendation_reason: Optional[str] = None
    recommendation_factors: Dict[str, Any] = {}
    lesson_ready: bool = False
    quiz_ready: bool = False
    evaluation_ready: bool = False
    quiz_question_count: int = 0
    numerical_target_ratio: float = 0.0
    actual_numerical_ratio: float = 0.0
    active_frontier: List[str] = []
    current_path: List[str] = []
    children_map: Dict[str, List[str]] = {}
    node_catalog: List[NodeHierarchyMeta] = []


class GraphNodeMutationResponse(BaseModel):
    session_id: str
    status: str = "updated"
    message: str
    current_node: str = ""
    added_node: Optional[NodeHierarchyMeta] = None
    added_nodes: List[NodeHierarchyMeta] = []
    removed_nodes: List[str] = []
    options: List[str] = []
    active_frontier: List[str] = []
    children_map: Dict[str, List[str]] = {}
    node_catalog: List[NodeHierarchyMeta] = []


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str  # initializing | running | ready | evaluating | completed | error | archived
    current_phase: Optional[str] = None
    topic: str = ""
    error_message: Optional[str] = None


class SessionSummary(BaseModel):
    session_id: str
    topic: str
    status: str
    created_at: str
    overall_progress: float = 0.0


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]
    total: int


# ── Search ────────────────────────────────────────────────────

class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    category: Optional[str] = None  # articles | videos | courses


class SearchResponse(BaseModel):
    query: str
    type: str = "all"  # articles | videos | courses | all
    results: List[SearchResult] = []
