import React from "react";
import {
  Box,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
  Wrap,
  WrapItem,
} from "@chakra-ui/react";

interface ActiveFilterItem {
  key: string;
  label: string;
  value: string;
}

interface ActiveFiltersBarProps {
  filters: ActiveFilterItem[];
  onClear: (key: string) => void;
}

const ActiveFiltersBar: React.FC<ActiveFiltersBarProps> = ({
  filters,
  onClear,
}) => {
  if (!filters.length) return null;

  return (
    <Box
      px={4}
      py={2}
      borderBottomWidth="1px"
      borderColor="gray.200"
      bg="gray.50"
    >
      <Wrap spacing={2} align="center">
        <WrapItem>
          <Text fontSize="sm" color="gray.600">
            Active Filters:
          </Text>
        </WrapItem>
        {filters.map((filter) => (
          <WrapItem key={`${filter.key}-${filter.value}`}>
            <Tag
              size="md"
              borderRadius="full"
              colorScheme="blue"
              variant="subtle"
            >
              <TagLabel>{`${filter.label}: ${filter.value}`}</TagLabel>
              <TagCloseButton onClick={() => onClear(filter.key)} />
            </Tag>
          </WrapItem>
        ))}
      </Wrap>
    </Box>
  );
};

export default ActiveFiltersBar;
