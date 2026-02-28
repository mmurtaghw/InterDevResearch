import React from "react";
import { Trial } from "../hooks/useTrials";
import { Button, ButtonProps } from "@chakra-ui/react";

interface Props {
  trial: Trial;
  onAddTrialToCollection: (selectedTrial: string) => void;
  onRemoveTrialFromCollection: (selectedTrial: string) => void;
  isInCollection: (trialId: string) => boolean;
  buttonProps?: ButtonProps; // Optional button props
}

const AddCollectionButton = ({
  trial,
  onAddTrialToCollection,
  onRemoveTrialFromCollection,
  isInCollection,
  buttonProps, // Include buttonProps in the destructuring
}: Props) => {
  const addToCollection = () => onAddTrialToCollection(trial.id);
  const removeFromCollection = () => onRemoveTrialFromCollection(trial.id);

  return (
    <>
      {isInCollection(trial.id) ? (
        <Button
          colorScheme="red"
          onClick={removeFromCollection}
          wordBreak={"break-word"}
          whiteSpace={"normal"}
          {...buttonProps} // Spread additional button properties
        >
          Remove from Collection
        </Button>
      ) : (
        <Button
          colorScheme="teal"
          whiteSpace={"normal"}
          wordBreak={"break-word"}
          onClick={addToCollection}
          {...buttonProps} // Spread additional button properties
        >
          Add to Collection
        </Button>
      )}
    </>
  );
};

export default AddCollectionButton;
