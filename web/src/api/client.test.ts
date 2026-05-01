import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "./client";

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockResponse(body: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(String(body)),
  });
}

beforeEach(() => vi.clearAllMocks());

describe("api.get", () => {
  it("returns parsed JSON on success", async () => {
    mockResponse({ id: "1" });
    const result = await api.get<{ id: string }>("/test");
    expect(result).toEqual({ id: "1" });
    expect(mockFetch).toHaveBeenCalledWith("/test", expect.objectContaining({ method: "GET" }));
  });

  it("throws on non-OK response", async () => {
    mockResponse("not found", 404);
    await expect(api.get("/test")).rejects.toThrow("HTTP 404");
  });
});

describe("api.post", () => {
  it("sends JSON body", async () => {
    mockResponse({ ok: true });
    await api.post("/test", { foo: "bar" });
    expect(mockFetch).toHaveBeenCalledWith(
      "/test",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ foo: "bar" }),
      }),
    );
  });
});

describe("api.delete", () => {
  it("returns undefined on 204", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: () => Promise.resolve(undefined),
      text: () => Promise.resolve(""),
    });
    const result = await api.delete("/test/1");
    expect(result).toBeUndefined();
  });
});
