namespace Freeform.Rigging.AimConstraintDialogue
{
    using System;
    using System.Diagnostics;
    using System.Windows;
    using System.Windows.Interop;

    /// <summary>
    /// Interaction logic for FrameRangeDialogue.xaml
    /// </summary>
    public partial class AimConstraintDialogue : Window
    {
        public AimConstraintDialogue()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public AimConstraintDialogue(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            AimConstraintDialogueVM vm = new AimConstraintDialogueVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            AimConstraintDialogueVM vm = DataContext as AimConstraintDialogueVM;
            vm.Close();
        }
    }
}
