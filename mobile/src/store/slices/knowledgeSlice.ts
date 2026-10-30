/**
 * Knowledge Slice - Redux Toolkit slice for knowledge unit management
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { KnowledgeUnit, SearchParams, SearchResult, SyncStatus } from '../../types';
import { getAPIService } from '../services/api';

interface KnowledgeState {
  items: Record<string, KnowledgeUnit>;
  searchResults: string[]; // Array of knowledge_ids
  filters: SearchParams['filters'];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
  syncStatus: SyncStatus;
}

const initialState: KnowledgeState = {
  items: {},
  searchResults: [],
  filters: {},
  loading: false,
  error: null,
  lastUpdated: null,
  syncStatus: {
    is_syncing: false,
    pending_changes: 0,
    network_connected: true,
  },
};

// Async thunks
export const searchKnowledge = createAsyncThunk(
  'knowledge/search',
  async (params: SearchParams, { rejectWithValue }) => {
    try {
      const api = getAPIService();
      const result = await api.searchKnowledge(params);
      return result;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const fetchKnowledgeUnit = createAsyncThunk(
  'knowledge/fetchById',
  async (id: string, { rejectWithValue }) => {
    try {
      const api = getAPIService();
      const unit = await api.getKnowledgeUnit(id);
      return unit;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const createKnowledgeUnit = createAsyncThunk(
  'knowledge/create',
  async (data: Partial<KnowledgeUnit>, { rejectWithValue }) => {
    try {
      const api = getAPIService();
      const unit = await api.createKnowledgeUnit(data);
      return unit;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const updateKnowledgeUnit = createAsyncThunk(
  'knowledge/update',
  async ({ id, data }: { id: string; data: Partial<KnowledgeUnit> }, { rejectWithValue }) => {
    try {
      const api = getAPIService();
      const unit = await api.updateKnowledgeUnit(id, data);
      return unit;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const deleteKnowledgeUnit = createAsyncThunk(
  'knowledge/delete',
  async (id: string, { rejectWithValue }) => {
    try {
      const api = getAPIService();
      await api.deleteKnowledgeUnit(id);
      return id;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

export const syncKnowledge = createAsyncThunk(
  'knowledge/sync',
  async (_, { rejectWithValue }) => {
    try {
      const api = getAPIService();
      // Implementation depends on offline sync logic
      return { success: true };
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);

const knowledgeSlice = createSlice({
  name: 'knowledge',
  initialState,
  reducers: {
    setFilters(state, action: PayloadAction<SearchParams['filters']>) {
      state.filters = action.payload;
    },
    clearSearchResults(state) {
      state.searchResults = [];
    },
    addLocalChange(state, action: PayloadAction<KnowledgeUnit>) {
      // Add to local state for offline mode
      state.items[action.payload.knowledge_id] = action.payload;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Search
    builder
      .addCase(searchKnowledge.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(searchKnowledge.fulfilled, (state, action) => {
        state.loading = false;
        state.searchResults = action.payload.results.map((u) => u.knowledge_id);
        action.payload.results.forEach((unit) => {
          state.items[unit.knowledge_id] = unit;
        });
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(searchKnowledge.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // Fetch by ID
    builder
      .addCase(fetchKnowledgeUnit.fulfilled, (state, action) => {
        state.items[action.payload.knowledge_id] = action.payload;
      });

    // Create
    builder
      .addCase(createKnowledgeUnit.fulfilled, (state, action) => {
        state.items[action.payload.knowledge_id] = action.payload;
      });

    // Update
    builder
      .addCase(updateKnowledgeUnit.fulfilled, (state, action) => {
        const id = action.payload.knowledge_id;
        if (state.items[id]) {
          state.items[id] = action.payload;
        }
      });

    // Delete
    builder
      .addCase(deleteKnowledgeUnit.fulfilled, (state, action) => {
        delete state.items[action.payload];
        state.searchResults = state.searchResults.filter((id) => id !== action.payload);
      });

    // Sync
    builder
      .addCase(syncKnowledge.pending, (state) => {
        state.syncStatus.is_syncing = true;
      })
      .addCase(syncKnowledge.fulfilled, (state) => {
        state.syncStatus.is_syncing = false;
        state.syncStatus.pending_changes = 0;
      })
      .addCase(syncKnowledge.rejected, (state, action) => {
        state.syncStatus.is_syncing = false;
        state.syncStatus.sync_error = action.payload as string;
      });
  },
});

export const {
  setFilters,
  clearSearchResults,
  addLocalChange,
  clearError,
} = knowledgeSlice.actions;

export const selectKnowledgeItems = (state: { knowledge: KnowledgeState }) =>
  state.knowledge.items;

export const selectSearchResults = (state: { knowledge: KnowledgeState }) =>
  state.knowledge.searchResults;

export const selectFilters = (state: { knowledge: KnowledgeState }) =>
  state.knowledge.filters;

export const selectLoading = (state: { knowledge: KnowledgeState }) =>
  state.knowledge.loading;

export const selectError = (state: { knowledge: KnowledgeState }) =>
  state.knowledge.error;

export const selectSyncStatus = (state: { knowledge: KnowledgeState }) =>
  state.knowledge.syncStatus;

export default knowledgeSlice.reducer;