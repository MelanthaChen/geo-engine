import { beforeEach, describe, expect, it, vi } from "vitest";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/api/client", () => ({
  default: { post },
}));

import { startAuditValidation } from "./experimentLab";

describe("startAuditValidation", () => {
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue({ data: { status: "queued" } });
  });

  it("sends the user-selected strategy through the singular strategy field", async () => {
    await startAuditValidation({
      websiteId: 3,
      auditId: 11,
      opportunityId: 122,
      propertyName: "GeoAIResume",
      websiteUrl: "https://geoairesume-web-six.vercel.app/",
      opportunityTitle: "Topic coverage",
      opportunityDirection: "Improve topic coverage",
      strategy: "citation",
    });

    expect(post).toHaveBeenCalledOnce();
    expect(post).toHaveBeenCalledWith(
      "/api/v1/experiment-lab/teacher-validation",
      expect.objectContaining({
        audit_id: 11,
        opportunity_id: 122,
        strategy: "citation",
      }),
    );
  });
});
