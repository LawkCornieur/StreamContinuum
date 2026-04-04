import { openDB, IDBPDatabase } from 'idb';
import { WatchedItem } from '../types';

const DB_NAME = 'stream_continuum_db';
const STORE_NAME = 'history';

/**
 * Local database service using IndexedDB
 * Handles watched history and local state
 */
class LocalDB {
  private dbPromise: Promise<IDBPDatabase>;

  constructor() {
    this.dbPromise = openDB(DB_NAME, 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        }
      },
    });
  }

  async addToHistory(item: WatchedItem) {
    const db = await this.dbPromise;
    await db.put(STORE_NAME, {
      ...item,
      lastWatched: Date.now(),
    });
  }

  async getHistory(): Promise<WatchedItem[]> {
    const db = await this.dbPromise;
    const items = await db.getAll(STORE_NAME);
    return items.sort((a, b) => b.lastWatched - a.lastWatched);
  }

  async removeFromHistory(id: string) {
    const db = await this.dbPromise;
    await db.delete(STORE_NAME, id);
  }

  async clearHistory() {
    const db = await this.dbPromise;
    await db.clear(STORE_NAME);
  }
}

export const localDB = new LocalDB();
