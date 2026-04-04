export interface TraktMovie {
  title: string;
  year: number;
  ids: {
    trakt: number;
    slug: string;
    imdb?: string;
    tmdb?: number;
  };
}

export interface TraktShow {
  title: string;
  year: number;
  ids: {
    trakt: number;
    slug: string;
    imdb?: string;
    tmdb?: number;
  };
}

export interface TraktEpisode {
  season: number;
  number: number;
  title: string;
  ids: {
    trakt: number;
    imdb?: string;
    tmdb?: number;
  };
}

export interface WatchedItem {
  id: string; // trakt id or slug
  type: 'movie' | 'show';
  title: string;
  lastWatched: number;
  season?: number;
  episode?: number;
  poster?: string;
}
