namespace Freeform.Rigging.FrameRangeDialogue
{
    using System;
    using System.Diagnostics;
    using System.Windows;
    using System.Windows.Interop;

    /// <summary>
    /// Interaction logic for FrameRangeDialogue.xaml
    /// </summary>
    public partial class FrameRangeDialogue : Window
    {
        public FrameRangeDialogue()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public FrameRangeDialogue(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            FrameRangeDialogueVM vm = new FrameRangeDialogueVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            FrameRangeDialogueVM vm = DataContext as FrameRangeDialogueVM;
            vm.Close();
        }
    }
}
