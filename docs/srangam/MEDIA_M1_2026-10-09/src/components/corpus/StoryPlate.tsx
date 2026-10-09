/**
 * The picture of a story, and its graphic novel if there is one - CORPUS_MEDIA_C8_2026_10_09.
 *
 * Shown at the head of /corpus/stories/:docCode/:storyId. Quiet by design: if the pictures are not
 * there (C8 not applied, none approved, a loading failure), the story reads exactly as before.
 */
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookImage } from 'lucide-react';
import CorpusImage from '@/components/corpus/CorpusImage';
import { GeneratedNote, MediaStatus } from '@/components/corpus/MediaParts';
import { imagesHref, isMedia, isNovel, loadMedia, loadNovels, novelHref } from '@/lib/corpusMedia';

export default function StoryPlate({ docCode, storyId }: { docCode: string; storyId: number }) {
  const media = useQuery({
    queryKey: ['mirror', 'media', 'story', docCode, storyId],
    queryFn: () => loadMedia({ doc: docCode, story: storyId, k: 4 }),
    staleTime: 5 * 60 * 1000,
  });
  const novels = useQuery({
    queryKey: ['mirror', 'novels', 'doc', docCode],
    queryFn: () => loadNovels(docCode),
    staleTime: 5 * 60 * 1000,
  });
  const pic = media.data?.ok ? media.data.rows.filter(isMedia)[0] : undefined;
  const novel = novels.data?.ok ? novels.data.rows.filter(isNovel).find((n) => n.story_id === storyId) : undefined;
  if (!pic && !novel) return null;
  return (
    <div className="mb-6 space-y-3">
      {pic && (
        <figure className="max-w-3xl">
          <Link to={`${imagesHref(docCode)}&pic=${encodeURIComponent(pic.media_key)}`} aria-label="Open the picture at full size">
            <CorpusImage sha={pic.sha256} rendition={pic.has_display ? 'display' : 'thumb'} available={pic.has_display || pic.has_thumb}
              width={pic.width} height={pic.height} alt={pic.title ?? 'The picture of this story'} eager />
          </Link>
          <figcaption className="mt-2 space-y-1 text-sm">
            <span className="flex flex-wrap items-center gap-2">
              {pic.caption_en && <span className="font-serif text-foreground">{pic.caption_en}</span>}
              <MediaStatus status={pic.status} />
            </span>
            {pic.caption_hi && <span lang="hi" className="block font-devanagari text-foreground/90">{pic.caption_hi}</span>}
            <GeneratedNote model={pic.model} />
          </figcaption>
        </figure>
      )}
      {novel && (
        <Link to={novelHref(novel.novel_id)} className="inline-flex items-center gap-2 rounded-md border border-burgundy/40 px-3 py-1.5 text-sm text-burgundy hover:border-burgundy">
          <BookImage className="h-4 w-4" aria-hidden="true" />
          Read it as a graphic novel{novel.pages ? ` (${novel.pages} pages)` : ''}
          <MediaStatus status={novel.status === 'approved' ? 'approved' : novel.status === 'plan' ? 'being planned' : 'being drawn'} />
        </Link>
      )}
    </div>
  );
}
