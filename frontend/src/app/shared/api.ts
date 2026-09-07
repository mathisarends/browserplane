export function expectStatus<
  Response extends { status: number },
  Status extends Response["status"],
>(
  response: Response,
  status: Status,
  failure: string,
): asserts response is Extract<Response, { status: Status }> {
  if (response.status !== status) throw new Error(`${failure} (${response.status})`);
}
