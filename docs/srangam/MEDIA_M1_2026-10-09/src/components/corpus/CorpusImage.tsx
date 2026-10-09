/**
 * One picture of the working corpus - CORPUS_MEDIA_C8_2026_10_09.
 *
 * Holds its place at the picture's own proportions (no jump when it arrives), starts fetching only
 * when it comes near the screen, and says plainly when a picture is not on Drive yet or could not
 * be loaded. The bytes come through src/lib/corpusMedia.ts (the reader's token, never in a URL).
 */
import { useEffect, useRef, useState } from 'react';
import { ImageOff, Loader2 } from 'lucide-react';
import { pictureUrl, PictureError, type Rendition } from '@/lib/corpusMedia';

interface Props {
  sha: string | null | undefined;
  alt: string;
  rendition?: Rendition;
  /** False when the server has no file for it yet (has_thumb / has_display). */
  available?: boolean;
  width?: number | null;
  height?: number | null;
  className?: string;
  imgClassName?: string;
  /** Load at once (a picture that is the page's subject), not when it nears the screen. */
  eager?: boolean;
  /** A fixed frame ("4 / 3") instead of the picture's own proportions: a grid of even cards. */
  ratio?: string;
}

export default function CorpusImage({
  sha, alt, rendition = 'thumb', available = true, width, height, className = '', imgClassName = '', eager = false, ratio: frame,
}: Props) {
  const box = useRef<HTMLDivElement | null>(null);
  const [near, setNear] = useState(eager);
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (near || !box.current) return;
    if (typeof IntersectionObserver === 'undefined') { setNear(true); return; }
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) setNear(true); },
      { rootMargin: '300px 0px' });
    io.observe(box.current);
    return () => io.disconnect();
  }, [near]);

  useEffect(() => {
    if (!near || !sha || !available) return;
    let live = true;
    setError(null);
    pictureUrl(sha, rendition)
      .then((u) => { if (live) setSrc(u); })
      .catch((e: unknown) => { if (live) setError(e instanceof PictureError ? e.message : 'The picture could not be loaded.'); });
    return () => { live = false; };
  }, [near, sha, rendition, available]);

  const ratio = frame ?? (width && height && width > 0 && height > 0 ? `${width} / ${height}` : '4 / 3');
  return (
    <div ref={box} className={`relative overflow-hidden rounded-md bg-muted/60 ${className}`} style={{ aspectRatio: ratio }}>
      {src && <img src={src} alt={alt} decoding="async" className={`h-full w-full object-contain ${imgClassName}`} />}
      {!src && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 p-2 text-center text-xs text-muted-foreground">
          {!sha || !available ? (
            <><ImageOff className="h-5 w-5" aria-hidden="true" /><span>Picture to come</span></>
          ) : error ? (
            <><ImageOff className="h-5 w-5" aria-hidden="true" /><span>{error}</span></>
          ) : (
            <Loader2 className="h-5 w-5 animate-spin" aria-label="Loading the picture" />
          )}
        </div>
      )}
    </div>
  );
}
