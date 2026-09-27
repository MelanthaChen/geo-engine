import { beforeEach, describe, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/api/client", () => ({
  default: { post },
}));

import {
  previewDatasetGeneration,
  startDatasetGeneration,
  type DatasetGenerationRequest,
} from "./teacherPipeline";

const request: DatasetGenerationRequest = {
  property_id: 4,
  audit_id: 17,
  strategy: "citation",
  training_sample_count: 100,
  repetitions_per_context: 1,
  provider: "chatgpt",
  llm: "gpt-3.5-turbo",
  random_seed: 42,
  temperature: 0.7,
  confirmed: false,
};

describe("Teacher dataset generation API", () => {
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue({ data: { status: "queued" } });
  });

  it("previews 100 contexts and one repetition without paid-run confirmation", async () => {
    await previewDatasetGeneration(request);

    expect(post).toHaveBeenCalledWith(
      "/api/v1/teacher-pipeline/dataset-generation/preview",
      expect.objectContaining({
        training_sample_count: 100,
        repetitions_per_context: 1,
        confirmed: false,
      }),
    );
  });

  it("sets explicit confirmation only when the user starts generation", async () => {
    await startDatasetGeneration(request);

    expect(post).toHaveBeenCalledWith(
      "/api/v1/teacher-pipeline/dataset-generation/start",
      expect.objectContaining({
        training_sample_count: 100,
        repetitions_per_context: 1,
        strategy: "citation",
        confirmed: true,
      }),
    );
  });
});
