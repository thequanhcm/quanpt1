/**
 * SearchScreen Component
 * Main search interface for knowledge units
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { KnowledgeUnitCard } from '../components/KnowledgeUnitCard';
import {
  searchKnowledge,
  selectSearchResults,
  selectKnowledgeItems,
  selectLoading,
  selectError,
  setFilters,
} from '../store/slices/knowledgeSlice';
import { SearchParams, SearchFilters } from '../types';

const SearchScreen: React.FC = () => {
  const dispatch = useDispatch();
  const searchResults = useSelector(selectSearchResults);
  const knowledgeItems = useSelector(selectKnowledgeItems);
  const loading = useSelector(selectLoading);
  const error = useSelector(selectError);

  const [query, setQuery] = useState('');
  const [filters, setLocalFilters] = useState<SearchFilters>({});
  const [page, setPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);

  const LIMIT = 20;

  const items = searchResults.map((id) => knowledgeItems[id]).filter(Boolean);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;

    const params: SearchParams = {
      query: query.trim(),
      filters,
      limit: LIMIT,
      offset: (page - 1) * LIMIT,
    };

    try {
      await dispatch(searchKnowledge(params)).unwrap();
    } catch (err) {
      console.error('Search failed:', err);
    }
  }, [query, filters, page, dispatch]);

  const handleFilterChange = (newFilters: SearchFilters) => {
    setLocalFilters(newFilters);
    dispatch(setFilters(newFilters));
    setPage(1);
    handleSearch();
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setPage(1);
    await handleSearch();
    setRefreshing(false);
  };

  const handleLoadMore = () => {
    if (!loading) {
      setPage((prev) => prev + 1);
    }
  };

  const handleCardPress = (id: string) => {
    // Navigate to detail screen
    console.log('Navigate to detail:', id);
  };

  const handleCardLongPress = (id: string) => {
    // Show action sheet
    console.log('Long press:', id);
  };

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyTitle}>No results found</Text>
      <Text style={styles.emptyMessage}>
        Try adjusting your search query or filters
      </Text>
    </View>
  );

  const renderError = () => (
    <View style={styles.errorContainer}>
      <Text style={styles.errorTitle}>Search Error</Text>
      <Text style={styles.errorMessage}>{error}</Text>
      <TouchableOpacity style={styles.retryButton} onPress={handleSearch}>
        <Text style={styles.retryButtonText}>Retry</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Search Bar */}
      <View style={styles.searchBar}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search knowledge units..."
          placeholderTextColor="#9CA3AF"
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={handleSearch}
          returnKeyType="search"
        />
        <TouchableOpacity style={styles.searchButton} onPress={handleSearch}>
          <Text style={styles.searchButtonText}>Search</Text>
        </TouchableOpacity>
      </View>

      {/* Filter Buttons */}
      <View style={styles.filterBar}>
        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => handleFilterChange({ ...filters, knowledge_type: ['FACT'] })}
        >
          <Text style={styles.filterButtonText}>Facts</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => handleFilterChange({ ...filters, knowledge_type: ['LESSON_LEARNED'] })}
        >
          <Text style={styles.filterButtonText}>Lessons</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => handleFilterChange({ ...filters, status: ['VERIFIED'] })}
        >
          <Text style={styles.filterButtonText}>Verified</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => handleFilterChange({})}
        >
          <Text style={styles.filterButtonText}>Clear</Text>
        </TouchableOpacity>
      </View>

      {/* Results */}
      <FlatList
        data={items}
        keyExtractor={(item) => item.knowledge_id}
        renderItem={({ item }) => (
          <KnowledgeUnitCard
            unit={item}
            onPress={handleCardPress}
            onLongPress={handleCardLongPress}
          />
        )}
        ListEmptyComponent={items.length === 0 && !loading ? renderEmpty : null}
        ListFooterComponent={
          loading ? (
            <ActivityIndicator style={styles.loader} size="large" color="#3B82F6" />
          ) : items.length > 0 ? (
            <TouchableOpacity style={styles.loadMoreButton} onPress={handleLoadMore}>
              <Text style={styles.loadMoreText}>Load More</Text>
            </TouchableOpacity>
          ) : null
        }
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.5}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={['#3B82F6']}
          />
        }
        contentContainerStyle={styles.listContent}
      />

      {/* Error Overlay */}
      {error && !loading && renderError()}
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  searchBar: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  searchInput: {
    flex: 1,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: '#1F2937',
    marginRight: 12,
  },
  searchButton: {
    backgroundColor: '#3B82F6',
    borderRadius: 8,
    paddingHorizontal: 20,
    paddingVertical: 12,
    justifyContent: 'center',
  },
  searchButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  filterBar: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  filterButton: {
    backgroundColor: '#F3F4F6',
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
  },
  filterButtonText: {
    color: '#4B5563',
    fontSize: 14,
    fontWeight: '500',
  },
  listContent: {
    paddingVertical: 8,
  },
  loader: {
    marginVertical: 24,
  },
  loadMoreButton: {
    padding: 16,
    alignItems: 'center',
  },
  loadMoreText: {
    color: '#3B82F6',
    fontSize: 16,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  emptyMessage: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
  },
  errorContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  errorMessage: {
    fontSize: 16,
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: '#3B82F6',
    borderRadius: 8,
    paddingHorizontal: 32,
    paddingVertical: 12,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default SearchScreen;