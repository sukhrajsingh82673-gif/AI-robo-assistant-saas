import * as crypto from 'crypto';

export class WebhookVerifier {
  constructor(private secret: string, private toleranceSeconds: number = 300) {}

  public verify(msgId: string, payload: string, signatureHeader: string): boolean {
    const parts = Object.fromEntries(
      signatureHeader.split(',').map((p) => p.split('='))
    );
    if (!parts.t || !parts.v1) return false;

    const ts = parseInt(parts.t, 10);
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - ts) > this.toleranceSeconds) return false;

    const toSign = `${msgId}.${ts}.${payload}`;
    const expected = crypto.createHmac('sha256', this.secret).update(toSign).digest('hex');
    return crypto.timingSafeEqual(Buffer.from(parts.v1), Buffer.from(expected));
  }
}
