namespace Freeform.Rigging.ParticleConstraintDialogue
{
    using Freeform.Core.UI;
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using System.Text;
    using System.Threading.Tasks;

    public class ParticleConstraintDialogueVM : ViewModelBase
    {
        public event EventHandler BuildConstraintHandler;

        public RelayCommand BuildConstraintCommand { get; set; }

        bool _useOffset;
        public bool UseOffset
        {
            get { return _useOffset; }
            set
            {
                _useOffset = value;
                RaisePropertyChanged("UseOffset");
                RaisePropertyChanged("NotUseOffset");
            }
        }
        public bool NotUseOffset { get { return !UseOffset; } }


        float _offsetAmount;
        public float OffsetAmount
        {
            get { return _offsetAmount; }
            set
            {
                _offsetAmount = value;
                float[] valueSet = GetValuesFromOffset();
                Weight = valueSet[0];
                Smoothness = valueSet[1];
                RaisePropertyChanged("OffsetAmount");
            }
        }

        float _weight;
        public float Weight
        {
            get { return _weight; }
            set
            {
                _weight = value;
                RaisePropertyChanged("Weight");
            }
        }

        float _smoothness;
        public float Smoothness
        {
            get { return _smoothness; }
            set
            {
                _smoothness = value;
                RaisePropertyChanged("Smoothness");
            }
        }

        float _frameOffset;
        public float FrameOffset
        {
            get { return _frameOffset; }
            set
            {
                _frameOffset = value;
                RaisePropertyChanged("FrameOffset");
            }
        }


        public ParticleConstraintDialogueVM()
        {
            UseOffset = true;
            OffsetAmount = 0.5f;
            Weight = 0.65f;
            Smoothness = 2.0f;
            FrameOffset = -250;

            BuildConstraintCommand = new RelayCommand(BuildConstraintCall);
        }

        float[] GetValuesFromOffset()
        {
            float[] valueSet = new float[2];
            switch (OffsetAmount)
            {
                case 0.1f:
                    valueSet[0] = 1.00f;
                    valueSet[1] = 1.00f;
                    break;
                case 0.2f:
                    valueSet[0] = 0.91f;
                    valueSet[1] = 1.25f;
                    break;
                case 0.3f:
                    valueSet[0] = 0.83f;
                    valueSet[1] = 1.50f;
                    break;
                case 0.4f:
                    valueSet[0] = 0.74f;
                    valueSet[1] = 1.75f;
                    break;
                case 0.5f:
                    valueSet[0] = 0.65f;
                    valueSet[1] = 2.00f;
                    break;
                case 0.6f:
                    valueSet[0] = 0.61f;
                    valueSet[1] = 2.30f;
                    break;
                case 0.7f:
                    valueSet[0] = 0.57f;
                    valueSet[1] = 2.60f;
                    break;
                case 0.8f:
                    valueSet[0] = 0.53f;
                    valueSet[1] = 2.90f;
                    break;
                case 0.9f:
                    valueSet[0] = 0.49f;
                    valueSet[1] = 3.20f;
                    break;
                case 1.0f:
                    valueSet[0] = 0.45f;
                    valueSet[1] = 3.50f;
                    break;
            }

            return valueSet;
        }


        public void BuildConstraintCall(object sender)
        {
            ConstraintEventArgs eventArgs = new ConstraintEventArgs() 
            {
                Weight = Weight,
                Smoothness = Smoothness,
                FrameOffset = Math.Abs(FrameOffset)
            };
            BuildConstraintHandler?.Invoke(this, eventArgs);
        }


        public class ConstraintEventArgs : EventArgs
        {
            public float Weight;
            public float Smoothness;
            public float FrameOffset;
        }
    }
}
