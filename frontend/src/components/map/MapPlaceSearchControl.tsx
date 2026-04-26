import SearchIcon from '@mui/icons-material/Search'
import {
  Autocomplete,
  Box,
  CircularProgress,
  InputAdornment,
  Paper,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useState } from 'react'
import { searchPlaces, type PlaceSearchResult } from '../../api/placeSearch'
import { MAP_OVERLAY_Z } from './mapOverlayZIndex'

const MIN_QUERY_LENGTH = 3
const SEARCH_DEBOUNCE_MS = 350

interface MapPlaceSearchControlProps {
  onPlaceSelect: (place: PlaceSearchResult) => void
  topOffsetPx?: number
}

export function MapPlaceSearchControl({
  onPlaceSelect,
  topOffsetPx = 16,
}: MapPlaceSearchControlProps) {
  const [inputValue, setInputValue] = useState('')
  const [value, setValue] = useState<PlaceSearchResult | null>(null)
  const [options, setOptions] = useState<PlaceSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const query = inputValue.trim()
    if (query.length < MIN_QUERY_LENGTH) {
      setOptions([])
      setLoading(false)
      setError(null)
      return
    }

    const ac = new AbortController()
    const timer = window.setTimeout(() => {
      setLoading(true)
      setError(null)
      searchPlaces(query, ac.signal, { limit: 5 })
        .then((results) => {
          setOptions(results)
        })
        .catch((e: unknown) => {
          if (e instanceof Error && e.name === 'AbortError') return
          setOptions([])
          setError(e instanceof Error ? e.message : 'Place search failed')
        })
        .finally(() => {
          if (!ac.signal.aborted) setLoading(false)
        })
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timer)
      ac.abort()
    }
  }, [inputValue])

  const attribution = useMemo(() => {
    const first = options.find((option) => option.attribution)
    return first?.attribution ?? null
  }, [options])

  return (
    <Paper
      elevation={4}
      aria-label="Place search"
      sx={{
        position: 'absolute',
        top: { xs: topOffsetPx + 64, sm: topOffsetPx },
        left: { xs: 16, sm: 432 },
        right: { xs: 16, sm: 'auto' },
        zIndex: MAP_OVERLAY_Z.floatingAndHud,
        width: { xs: 'auto', sm: 360 },
        maxWidth: 'calc(100vw - 32px)',
        borderRadius: 2,
        bgcolor: 'rgba(255, 255, 255, 0.96)',
        backdropFilter: 'blur(8px)',
        border: 1,
        borderColor: 'divider',
        pointerEvents: 'auto',
      }}
    >
      <Box sx={{ p: 1 }}>
        <Autocomplete
          size="small"
          options={options}
          value={value}
          inputValue={inputValue}
          loading={loading}
          filterOptions={(x) => x}
          getOptionLabel={(option) => option.label}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          noOptionsText={
            inputValue.trim().length < MIN_QUERY_LENGTH
              ? 'Type at least 3 characters'
              : error
                ? error
                : 'No matching places'
          }
          onInputChange={(_, newValue, reason) => {
            if (reason === 'reset') return
            setInputValue(newValue)
          }}
          onChange={(_, newValue) => {
            setValue(newValue)
            if (newValue) onPlaceSelect(newValue)
          }}
          renderOption={(props, option) => (
            <li {...props} key={option.id}>
              <Typography variant="body2" sx={{ whiteSpace: 'normal', lineHeight: 1.3 }}>
                {option.label}
              </Typography>
            </li>
          )}
          renderInput={(params) => (
            <TextField
              {...params}
              placeholder="Search place or postcode"
              aria-label="Search place or postcode"
              error={Boolean(error)}
              InputProps={{
                ...params.InputProps,
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <>
                    {loading ? <CircularProgress color="inherit" size={16} /> : null}
                    {params.InputProps.endAdornment}
                  </>
                ),
              }}
            />
          )}
        />
        {attribution && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', mt: 0.5, px: 0.5 }}
          >
            {attribution}
          </Typography>
        )}
      </Box>
    </Paper>
  )
}
