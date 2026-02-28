import React, { useState } from "react";
import { Trial } from "../hooks/useTrials";
import {
  Card,
  CardBody,
  Heading,
  Text,
  Box,
  HStack,
  Button,
} from "@chakra-ui/react";
import slugify from "slugify";
import { useNavigate } from "react-router-dom";
import AddCollectionButton from "./AddCollectionButton";

interface Props {
  game: Trial;
  onSelectTrial: (selectedTrial: Trial) => void;
  onAddTrialToCollection: (selectedTrial: string) => void;
  onRemoveTrialFromCollection: (selectedTrial: string) => void;
  isInCollection: (trialId: string) => boolean;
}

const GameCard = ({
  game,
  onSelectTrial,
  onAddTrialToCollection,
  onRemoveTrialFromCollection,
  isInCollection,
}: Props) => {
  const [isHovering, setIsHovering] = useState(false);
  const navigate = useNavigate();

  const handleViewClick = () => {
    onSelectTrial(game);
    navigate(`/trial/${slugify(game.Title || "undefined")}`);
  };

  return (
    <Card
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      cursor={isHovering ? "default" : "pointer"} // Changes cursor style based on hovering state
      _hover={{ boxShadow: "lg", transform: "scale(1.05)" }}
      position="relative"
      transition="0.3s ease-in-out"
    >
      <CardBody paddingBottom={isHovering ? "80px" : "20px"}>
        <Heading fontSize={"xl"}>{game.Title}</Heading>
        <Text fontSize={"md"} fontWeight="bold">
          By: {game.Authors}
        </Text>
        <Box
          fontSize={"sm"}
          overflow="hidden"
          textOverflow="ellipsis"
          noOfLines={4}
        >
          {game.Abstract}
        </Box>
        {isHovering && (
          <HStack
            position="absolute"
            bottom="15px"
            width="half"
            paddingX="10px"
            justifyContent="space-between"
            spacing={2}
          >
            <Button size="sm" onClick={handleViewClick} width="auto">
              View
            </Button>
            <AddCollectionButton
              trial={game}
              onAddTrialToCollection={onAddTrialToCollection}
              onRemoveTrialFromCollection={onRemoveTrialFromCollection}
              isInCollection={isInCollection}
              buttonProps={{
                size: "sm",
                width: "auto",
                whiteSpace: "normal",
                wordBreak: "break-word",
              }}
            />
          </HStack>
        )}
      </CardBody>
    </Card>
  );
};

export default GameCard;
